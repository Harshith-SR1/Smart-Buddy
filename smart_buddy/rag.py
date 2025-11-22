"""RAG Knowledge Base with hybrid retrieval and freshness controls.

Implements document ingestion, hybrid (vector + keyword) retrieval, citation
responses, and golden-question benchmarking to push toward top-tier rankings.
"""
from __future__ import annotations

import json
import math
import pickle
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import numpy as np  # type: ignore

    NUMPY_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore

    EMBEDDINGS_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    SentenceTransformer = None  # type: ignore[assignment]
    EMBEDDINGS_AVAILABLE = False

from smart_buddy.logging import get_logger
from smart_buddy.llm import LLM

STOPWORDS = {
    "the",
    "and",
    "you",
    "for",
    "that",
    "with",
    "are",
    "this",
    "was",
    "but",
    "have",
    "not",
    "your",
    "from",
    "will",
    "then",
    "been",
    "into",
    "about",
    "when",
    "what",
    "will",
    "their",
    "there",
}


@dataclass
class DocumentChunk:
    doc_id: str
    chunk_id: str
    title: str
    source: str
    content: str
    updated_at: float
    embedding: List[float]
    keywords: Counter

    @property
    def citation(self) -> str:
        return f"{self.title} ({self.source}) • chunk {self.chunk_id}"


class _FallbackEncoder:
    """Deterministic bag-of-words encoder when transformers unavailable."""

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        vectors: List[List[float]] = []
        for text in texts:
            tokens = re.findall(r"[a-z0-9]+", text.lower())
            tok_counts = Counter(tokens)
            sorted_items = sorted(tok_counts.items())
            vec = [0.0] * 256
            for token, count in sorted_items:
                idx = hash(token) % 256
                vec[idx] += float(count)
            norm = math.sqrt(sum(v * v for v in vec))
            if norm:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


class RAGKnowledgeBase:
    def __init__(
        self,
        storage_path: str = "data/rag_store.pkl",
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if EMBEDDINGS_AVAILABLE and SentenceTransformer is not None:
            self.encoder: Any = SentenceTransformer(model_name)  # type: ignore[misc]
        else:
            self.encoder = _FallbackEncoder()
        self._logger = get_logger(__name__)
        self.records: List[DocumentChunk] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            self.records = []
            return
        try:
            raw = pickle.loads(self.storage_path.read_bytes())
            self.records = [
                DocumentChunk(
                    doc_id=entry["doc_id"],
                    chunk_id=entry["chunk_id"],
                    title=entry["title"],
                    source=entry["source"],
                    content=entry["content"],
                    updated_at=entry["updated_at"],
                    embedding=self._to_vector(entry.get("embedding", [])),
                    keywords=Counter(entry["keywords"]),
                )
                for entry in raw.get("records", [])
            ]
        except Exception:
            self._logger.exception("rag_load_failed")
            self.records = []

    def _save(self) -> None:
        data = {
            "records": [
                {
                    "doc_id": rec.doc_id,
                    "chunk_id": rec.chunk_id,
                    "title": rec.title,
                    "source": rec.source,
                    "content": rec.content,
                    "updated_at": rec.updated_at,
                    "embedding": list(rec.embedding),
                    "keywords": dict(rec.keywords),
                }
                for rec in self.records
            ]
        }
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_bytes(pickle.dumps(data))

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest_documents(self, documents: List[Dict]) -> int:
        """Add documents to the store via chunking pipeline."""
        new_records: List[DocumentChunk] = []
        now = time.time()
        for doc in documents:
            title = doc.get("title") or doc.get("id") or "Untitled"
            source = doc.get("source", "local")
            doc_id = doc.get("id") or f"doc-{hash(title) % 10_000}"
            updated_at = float(doc.get("updated_at", now))
            for idx, chunk_text in enumerate(self._chunk(doc.get("content", ""))):
                emb = self.encoder.encode([chunk_text])[0]
                keywords = self._keywords(chunk_text)
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    chunk_id=f"{idx+1}",
                    title=title,
                    source=source,
                    content=chunk_text,
                    updated_at=updated_at,
                    embedding=self._to_vector(emb),
                    keywords=keywords,
                )
                new_records.append(chunk)
        if new_records:
            self.records.extend(new_records)
            self._save()
        self._logger.info(
            "rag_ingest",
            extra={"documents": len(documents), "chunks": len(new_records)},
        )
        return len(new_records)

    def ingest_directory(self, directory: str, glob: str = "*.md") -> int:
        docs: List[Dict] = []
        base = Path(directory)
        for path in base.rglob(glob):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            docs.append(
                {
                    "id": path.stem,
                    "title": path.stem.replace("_", " ").title(),
                    "source": str(path.relative_to(base)),
                    "content": content,
                    "updated_at": path.stat().st_mtime,
                }
            )
        return self.ingest_documents(docs)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 5,
        freshness_window_days: int = 45,
    ) -> List[Dict]:
        if not query.strip():
            return []
        query_emb = self.encoder.encode([query])[0]
        query_keywords = self._keywords(query)
        now = time.time()
        scored = []
        for rec in self.records:
            vector_score = self._cosine(query_emb, rec.embedding)
            keyword_score = self._keyword_overlap(query_keywords, rec.keywords)
            recency_days = max(0.0, (now - rec.updated_at) / 86_400)
            freshness = max(0.2, 1 - (recency_days / freshness_window_days))
            total = 0.6 * vector_score + 0.3 * keyword_score + 0.1 * freshness
            scored.append((total, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict] = []
        for score, rec in scored[:top_k]:
            results.append(
                {
                    "score": float(score),
                    "content": rec.content,
                    "citation": rec.citation,
                    "source": rec.source,
                    "title": rec.title,
                    "updated_at": rec.updated_at,
                }
            )
        return results

    def build_context(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return ""
        parts = []
        for res in results:
            snippet = res["content"].strip().replace("\n", " ")
            parts.append(f"[{res['citation']}] {snippet}")
        return "\n".join(parts)

    def answer_question(
        self,
        query: str,
        llm: Optional[LLM] = None,
        top_k: int = 3,
    ) -> Dict:
        context = self.build_context(query, top_k=top_k)
        if not context:
            return {
                "answer": "I do not have relevant knowledge for that yet.",
                "citations": [],
            }
        llm = llm or LLM()
        prompt = (
            "You are a grounded assistant. Use ONLY the provided context to answer.\n"
            "If the answer is not in the context, say you don't know.\n"
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )
        response = llm.generate(prompt)
        answer = (
            response.get("candidates", [{}])[0].get("content")
            if isinstance(response, dict)
            else None
        )
        answer = answer or "Unable to answer from current knowledge base."
        citations = [res["citation"] for res in self.search(query, top_k=top_k)]
        return {"answer": answer.strip(), "citations": citations}

    # ------------------------------------------------------------------
    # Freshness & Benchmarking
    # ------------------------------------------------------------------
    def apply_freshness_policy(self, max_age_days: int = 365) -> int:
        cutoff = time.time() - max_age_days * 86_400
        before = len(self.records)
        self.records = [rec for rec in self.records if rec.updated_at >= cutoff]
        removed = before - len(self.records)
        if removed:
            self._save()
        self._logger.info(
            "rag_freshness_policy",
            extra={"removed": removed, "max_age_days": max_age_days},
        )
        return removed

    def evaluate_golden_questions(
        self,
        questions: List[Dict[str, Any]],
        top_k: int = 3,
        report_path: str = "reports/rag_benchmarks.json",
    ) -> Dict:
        if not questions:
            return {"accuracy": 0.0, "total": 0, "details": []}
        correct = 0
        details = []
        for item in questions:
            query = str(item.get("question", ""))
            expected_sources = item.get("expected_sources", []) or []
            expected = set(expected_sources)
            hits = self.search(query, top_k=top_k)
            hit_sources = {hit["source"] for hit in hits}
            success = bool(expected & hit_sources)
            if success:
                correct += 1
            details.append({
                "question": query,
                "expected": list(expected),
                "hit_sources": list(hit_sources),
                "success": success,
            })
        accuracy = correct / len(questions)
        report = {"accuracy": accuracy, "total": len(questions), "details": details}
        report_file = Path(report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        self._logger.info(
            "rag_benchmark",
            extra={"accuracy": accuracy, "questions": len(questions)},
        )
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _to_vector(self, data: Any) -> List[float]:
        if data is None:
            return []
        if NUMPY_AVAILABLE and np is not None and hasattr(data, "tolist"):
            return [float(x) for x in data.tolist()]
        if isinstance(data, (list, tuple)):
            return [float(x) for x in data]
        return [float(data)]

    def _chunk(self, text: str, max_words: int = 180) -> List[str]:
        cleaned = text.replace("\r", "")
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        chunks: List[str] = []
        for para in paragraphs:
            words = para.split()
            for i in range(0, len(words), max_words):
                chunk_words = words[i : i + max_words]
                chunk = " ".join(chunk_words)
                if chunk:
                    chunks.append(chunk)
        if not chunks and text.strip():
            chunks.append(text.strip())
        return chunks

    def _keywords(self, text: str) -> Counter:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        filtered = [tok for tok in tokens if tok not in STOPWORDS and len(tok) > 2]
        return Counter(filtered)

    def _keyword_overlap(self, q: Counter, d: Counter) -> float:
        numerator = sum(min(q[token], d.get(token, 0)) for token in q)
        denominator = sum(q.values()) or 1
        return numerator / denominator

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if NUMPY_AVAILABLE and np is not None:
            a_arr = np.asarray(a, dtype=float)
            b_arr = np.asarray(b, dtype=float)
            if not np.any(a_arr) or not np.any(b_arr):
                return 0.0
            denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
            if denom == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / denom)
        if not a or not b:
            return 0.0
        limit = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(limit))
        norm_a = math.sqrt(sum(a[i] * a[i] for i in range(limit)))
        norm_b = math.sqrt(sum(b[i] * b[i] for i in range(limit)))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))


__all__ = ["RAGKnowledgeBase", "DocumentChunk"]

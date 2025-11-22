import json
import os
import tempfile
import time

from smart_buddy.rag import RAGKnowledgeBase


def make_store(tmp_path: str) -> RAGKnowledgeBase:
    return RAGKnowledgeBase(storage_path=tmp_path)


def test_rag_hybrid_retrieval_prefers_matching_doc():
    fd, path = tempfile.mkstemp(prefix="sb_rag_", suffix=".pkl")
    os.close(fd)
    try:
        kb = make_store(path)
        kb.ingest_documents(
            [
                {
                    "id": "doc_strategy",
                    "title": "AI Launch Strategy",
                    "source": "docs/ai_strategy.md",
                    "content": "Launch plan with weekly cadences and OKRs for AI agent competition.",
                },
                {
                    "id": "doc_general",
                    "title": "Gardening Tips",
                    "source": "docs/garden.md",
                    "content": "How to water plants in summer.",
                },
            ]
        )
        results = kb.search("weekly AI competition roadmap", top_k=1)
        assert results
        assert "ai_strategy" in results[0]["source"]
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rag_freshness_policy_and_scoring():
    fd, path = tempfile.mkstemp(prefix="sb_rag_fresh_", suffix=".pkl")
    os.close(fd)
    try:
        kb = make_store(path)
        stale_time = time.time() - 200 * 86_400
        kb.ingest_documents(
            [
                {
                    "id": "stale_doc",
                    "title": "Old Spec",
                    "source": "docs/spec_old.md",
                    "content": "Legacy instructions for deprecated stack.",
                    "updated_at": stale_time,
                },
                {
                    "id": "fresh_doc",
                    "title": "New Spec",
                    "source": "docs/spec_new.md",
                    "content": "Modern guidance for Smart Buddy plan-execute-reflect loop.",
                },
            ]
        )
        top_hit = kb.search("plan execute reflect loop", top_k=1)[0]
        assert "spec_new" in top_hit["source"]
        removed = kb.apply_freshness_policy(max_age_days=180)
        assert removed == 1
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rag_golden_question_benchmark():
    fd, path = tempfile.mkstemp(prefix="sb_rag_bench_", suffix=".pkl")
    os.close(fd)
    report_dir = tempfile.mkdtemp(prefix="sb_rag_report_")
    report_path = os.path.join(report_dir, "report.json")
    try:
        kb = make_store(path)
        kb.ingest_documents(
            [
                {
                    "id": "eval_doc",
                    "title": "Evaluation Playbook",
                    "source": "docs/eval.md",
                    "content": "Golden question answers for judges.",
                }
            ]
        )
        questions = [
            {
                "question": "What is inside the evaluation playbook?",
                "expected_sources": ["docs/eval.md"],
            }
        ]
        report = kb.evaluate_golden_questions(questions, report_path=report_path)
        assert report["accuracy"] == 1.0
        assert os.path.exists(report_path)
        with open(report_path, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
        assert stored["total"] == 1
    finally:
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(report_path):
            os.remove(report_path)
        if os.path.isdir(report_dir):
            try:
                os.rmdir(report_dir)
            except OSError:
                pass
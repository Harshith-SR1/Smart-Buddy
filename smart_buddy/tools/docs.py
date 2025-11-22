"""Docs lookup tool for agent planner."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .base import Tool, ToolRequest, ToolResult


@dataclass
class _DocRecord:
    path: Path
    title: str
    content: str


class DocumentLookupTool(Tool):
    name = "docs.lookup"
    description = "Search project documentation for keywords"
    guardrails = {"max_args": 4, "max_query_len": 160}

    def __init__(self, docs_root: str | Path = "docs") -> None:
        super().__init__()
        self.docs_root = Path(docs_root)
        self._records: List[_DocRecord] = []
        self._index_docs()

    def _index_docs(self) -> None:
        if not self.docs_root.exists():
            return
        for path in self.docs_root.rglob("*.md"):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:  # pragma: no cover - best effort
                continue
            title = path.stem.replace("_", " ").title()
            snippet = " ".join(content.split())[:1200]
            self._records.append(_DocRecord(path=path, title=title, content=snippet))

    def invoke(self, request: ToolRequest) -> ToolResult:
        query = str(request.arguments.get("query") or "").strip()
        if not query or len(query) > self.guardrails["max_query_len"]:
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": "invalid_query"},
            )
        hits: List[Dict[str, str]] = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        for record in self._records[:25]:
            if pattern.search(record.content):
                hits.append(
                    {
                        "title": record.title,
                        "path": str(record.path),
                        "excerpt": record.content[:240] + "…",
                    }
                )
            if len(hits) >= 3:
                break
        return ToolResult(
            name=self.name,
            success=True,
            output={"hits": hits},
            diagnostics={"query": query, "hit_count": len(hits)},
        )

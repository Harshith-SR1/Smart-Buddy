"""Curated offline web search tool."""
from __future__ import annotations

from typing import List, TypedDict

from .base import Tool, ToolRequest, ToolResult


class _CuratedResult(TypedDict):
    title: str
    url: str
    summary: str
    tags: List[str]


_CURATED_RESULTS: List[_CuratedResult] = [
    {
        "title": "AI Observability Basics",
        "url": "https://example.org/observability",
        "summary": "Explains latency percentiles, trace IDs, and metrics useful for agent systems.",
        "tags": ["metrics", "observability"],
    },
    {
        "title": "Tool Orchestration Blueprint",
        "url": "https://example.org/tools",
        "summary": "Patterns for secure tool execution, guardrails, and audit logging.",
        "tags": ["tools", "security"],
    },
    {
        "title": "Education Benchmarks 2025",
        "url": "https://example.org/edu-bench",
        "summary": "Latest data on AI tutor effectiveness across 50 judge scenarios.",
        "tags": ["education", "benchmarks"],
    },
]


class CuratedWebSearchTool(Tool):
    name = "web.search"
    description = "Offline curated search results"
    guardrails = {"max_args": 4, "allowed_tags": {"metrics", "tools", "education"}}

    def invoke(self, request: ToolRequest) -> ToolResult:
        query = str(request.arguments.get("query") or "").lower()
        tag = str(request.arguments.get("tag") or "").lower()
        hits: List[_CuratedResult] = []
        for result in _CURATED_RESULTS:
            if query and query not in result["summary"].lower() and query not in result["title"].lower():
                continue
            if tag and tag not in self.guardrails["allowed_tags"]:
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": "unsafe_tag"},
                )
            if tag and tag not in result["tags"]:
                continue
            hits.append(result)
        return ToolResult(
            name=self.name,
            success=True,
            output={"hits": hits[:3]},
            diagnostics={"query": query, "tag": tag, "hit_count": len(hits[:3])},
        )

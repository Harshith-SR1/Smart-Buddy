"""Calendar plugin used by planner/tool registry."""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List

from smart_buddy.memory import MemoryBank
from .base import Tool, ToolRequest, ToolResult


class CalendarTool(Tool):
    name = "calendar.manage"
    description = "Create lightweight calendar holds or list upcoming events"
    guardrails = {
        "max_args": 6,
        "allowed_actions": {"list_upcoming", "add_hold"},
    }

    def __init__(self, memory: MemoryBank | None = None) -> None:
        super().__init__()
        self.memory = memory or MemoryBank()
        self._namespace = "events"

    def is_allowed(self, request: ToolRequest) -> bool:
        if not super().is_allowed(request):
            return False
        action = request.arguments.get("action") or "list_upcoming"
        return action in self.guardrails["allowed_actions"]

    def invoke(self, request: ToolRequest) -> ToolResult:
        action = request.arguments.get("action") or "list_upcoming"
        if action == "add_hold":
            return self._add_hold(request)
        return self._list_upcoming(request)

    # ------------------------------------------------------------------
    def _list_upcoming(self, request: ToolRequest) -> ToolResult:
        events: List[Dict[str, Any]] = (
            self.memory.get(self._namespace, request.user_id, []) or []
        )
        upcoming = events[-3:][::-1]
        return ToolResult(
            name=self.name,
            success=True,
            output={"events": upcoming},
            diagnostics={"count": len(upcoming)},
        )

    def _add_hold(self, request: ToolRequest) -> ToolResult:
        title = str(request.arguments.get("title") or "Hold").strip()[:80]
        if not title:
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": "missing_title"},
            )
        date_str = request.arguments.get("date")
        try:
            date = _dt.datetime.fromisoformat(str(date_str))
        except Exception:
            date = _dt.datetime.utcnow() + _dt.timedelta(days=1)
        event = {
            "title": title,
            "date": date.isoformat(),
            "time": request.arguments.get("time", "09:00"),
            "source": "tool_bus",
        }
        events: List[Dict[str, Any]] = (
            self.memory.get(self._namespace, request.user_id, []) or []
        )
        events.append(event)
        self.memory.set(self._namespace, request.user_id, events, trace_id=request.trace_id)
        return ToolResult(
            name=self.name,
            success=True,
            output={"created": event},
            diagnostics={"total_events": len(events)},
        )

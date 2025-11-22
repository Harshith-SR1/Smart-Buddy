"""Centralized audit trail for moderation, memory, and tool events."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from smart_buddy.logging import get_logger


class AuditTrail:
    def __init__(self, max_events: int = 500) -> None:
        self._lock = threading.Lock()
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)
        self._next_id = 1
        self._logger = get_logger("smart_buddy.audit")

    def record(
        self,
        event_type: str,
        *,
        trace_id: Optional[str] = None,
        severity: str = "info",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            event = {
                "id": self._next_id,
                "event_type": event_type,
                "trace_id": trace_id or "unknown",
                "severity": severity,
                "payload": payload or {},
                "timestamp": time.time(),
                "status": "open",
                "notes": [],
            }
            self._events.appendleft(event)
            self._next_id += 1
        self._logger.info(
            "audit_event",
            extra={"event_type": event_type, "trace_id": trace_id, "severity": severity},
        )
        return event

    def override(self, event_id: int, note: str, actor: str = "manual") -> bool:
        with self._lock:
            for event in self._events:
                if event["id"] == event_id:
                    event["status"] = "overridden"
                    event["notes"].append({"actor": actor, "note": note, "timestamp": time.time()})
                    self._logger.info("audit_override", extra={"event_id": event_id, "actor": actor})
                    return True
        return False

    def list_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        if limit is not None:
            return events[:limit]
        return events

    def export(self) -> List[Dict[str, Any]]:
        return self.list_events()


audit_trail = AuditTrail()

__all__ = ["audit_trail", "AuditTrail"]

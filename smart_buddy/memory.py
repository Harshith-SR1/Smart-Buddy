"""Simple SQLite-backed namespaced Memory Bank for Smart Buddy.

Provides a tiny key/value store with JSON values and a small API
suitable for session memory, task persistence, and planner checkpoints.
"""

import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
from .logging import get_logger
from .audit import audit_trail


class MemoryBank:
    def __init__(self, db_path: Optional[str] = None):
        # default to a file in the repo if not provided to aid debugging
        self.db_path = db_path or "smart_buddy_memory.db"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at REAL,
                PRIMARY KEY(namespace, key)
            )
            """
        )
        self._conn.commit()
        self._logger = get_logger(__name__)

    def close(self):
        with self._lock:
            try:
                self._conn.close()
                self._logger.info("db_closed", extra={"db_path": self.db_path})
            except Exception:
                self._logger.exception("db_close_failed")

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, default=str, ensure_ascii=False)

    def _deserialize(self, raw: Optional[str]) -> Any:
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def set(
        self, namespace: str, key: str, value: Any, trace_id: Optional[str] = None
    ) -> None:
        raw = self._serialize(value)
        now = time.time()
        with self._lock:
            self._conn.execute(
                "REPLACE INTO kv (namespace, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (namespace, key, raw, now),
            )
            self._conn.commit()
        extra = {"namespace": namespace, "key": key, "value_preview": str(raw)[:200]}
        if trace_id:
            extra["trace_id"] = trace_id
        self._logger.debug("kv_set", extra=extra)
        audit_trail.record(
            "memory_write",
            trace_id=trace_id,
            payload={"namespace": namespace, "key": key, "value_preview": str(value)[:120]},
        )

    def get(
        self,
        namespace: str,
        key: str,
        default: Any = None,
        trace_id: Optional[str] = None,
    ) -> Any:
        cur = self._conn.execute(
            "SELECT value FROM kv WHERE namespace = ? AND key = ?", (namespace, key)
        )
        row = cur.fetchone()
        if not row:
            return default
        val = self._deserialize(row[0])
        extra = {"namespace": namespace, "key": key}
        if trace_id:
            extra["trace_id"] = trace_id
        self._logger.debug("kv_get", extra=extra)
        return val

    def delete(self, namespace: str, key: str, trace_id: Optional[str] = None) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM kv WHERE namespace = ? AND key = ?", (namespace, key)
            )
            self._conn.commit()
            deleted = cur.rowcount > 0
            extra = {"namespace": namespace, "key": key, "deleted": deleted}
            if trace_id:
                extra["trace_id"] = trace_id
            self._logger.debug("kv_delete", extra=extra)
        audit_trail.record(
            "memory_delete",
            trace_id=trace_id,
            payload={"namespace": namespace, "key": key, "deleted": deleted},
        )
        return deleted

    def keys(self, namespace: str) -> List[str]:
        cur = self._conn.execute("SELECT key FROM kv WHERE namespace = ?", (namespace,))
        return [r[0] for r in cur.fetchall()]

    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        cur = self._conn.execute(
            "SELECT key, value FROM kv WHERE namespace = ?", (namespace,)
        )
        return {r[0]: self._deserialize(r[1]) for r in cur.fetchall()}

    def append_to_list(
        self, namespace: str, key: str, item: Any, trace_id: Optional[str] = None
    ) -> None:
        lst = self.get(namespace, key, []) or []
        if not isinstance(lst, list):
            lst = [lst]
        lst.append(item)
        self.set(namespace, key, lst, trace_id=trace_id)
        extra = {"namespace": namespace, "key": key, "item_preview": str(item)[:200]}
        if trace_id:
            extra["trace_id"] = trace_id
        self._logger.debug("kv_append", extra=extra)

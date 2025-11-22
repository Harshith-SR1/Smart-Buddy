"""Small structured-logging helper for Smart Buddy.

Provides a lightweight JSON formatter and `get_logger` helper so modules
can emit structured logs without adding external dependencies.

Keep this intentionally small to avoid dependency churn for the project.
"""

import json
import logging
import time


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Don't output logs to console during interactive chat
        return ""

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

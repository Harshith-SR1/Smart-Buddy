"""Simple Intent Agent (skeleton).
This agent demonstrates intent classification used by the Router.
"""

from typing import Optional, TypedDict
from smart_buddy.logging import get_logger


class IntentPrediction(TypedDict):
    intent: str
    confidence: str


class IntentAgent:
    def __init__(self):
        self._logger = get_logger(__name__)

    def classify(self, text: str, trace_id: Optional[str] = None) -> IntentPrediction:
        """Return a simple intent classification.

        This is rule-based for the prototype. Returns dict with 'intent' and optional 'confidence'.
        Logs the classification with `trace_id` when available.
        """
        t = text.lower()
        intent: IntentPrediction
        # Mentor mode: teaching, learning, advice, planning, problem-solving, review
        if any(k in t for k in ("teach", "explain", "learn", "what is", "how does", "advice", "suggest", "plan", "roadmap", "problem", "stuck", "review", "feedback")):
            intent = {"intent": "planner", "confidence": "0.9"}
        elif any(k in t for k in ("task", "todo", "remind", "reminder", "add event", "schedule", "calendar")):
            intent = {"intent": "task", "confidence": "0.9"}
        elif any(
            k in t
            for k in ("sad", "stress", "anx", "feel", "upset", "depress", "lonely", "happy", "excited")
        ):
            intent = {"intent": "emotion", "confidence": "0.9"}
        elif any(k in t for k in ("summary", "summarize", "tl;dr", "summ")):
            intent = {"intent": "summary", "confidence": "0.8"}
        else:
            intent = {"intent": "general", "confidence": "0.6"}

        extra = {"text_preview": text[:120], "intent": intent}
        if trace_id:
            extra["trace_id"] = trace_id
        self._logger.info("intent_classified", extra=extra)
        return intent

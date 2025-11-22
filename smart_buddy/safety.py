"""
Simple, local content-safety checks for Smart Buddy.

This module provides a lightweight moderation utility that:
- runs keyword/phrase checks for disallowed content categories
- applies basic regex checks (PII) and length checks
- returns a structured moderation result that can be used to block or tag prompts

Note: This is intentionally simple so it works offline. For production use
replace or augment this with a call to a moderated cloud API (e.g., Google
Content API or an external moderation provider).
"""

import re
from typing import Dict, List, Optional

from smart_buddy.audit import audit_trail

# Categories of disallowed keywords (small, extensible lists)
_DISALLOWED = {
    "sexual": ["porn", "sexual", "sex with", "rape", "incest", "bestiality"],
    "violence": ["kill", "murder", "assassinat", "bomb", "explode", "torture"],
    "self_harm": ["suicide", "kill myself", "self-harm"],
    "illegal": [
        "how to make a bomb",
        "explosive",
        "drug lab",
        "hack into",
        "carding",
        "steal credentials",
    ],
    "hate": [
        # intentionally generic; do NOT include slurs here in the repo; this is illustrative
        "kill all",
        "degrade",
        "hate speech",
    ],
}

# Simple PII patterns (very conservative)
_PII_PATTERNS = {
    "credit_card": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
}

# Minimum/maximum sizes
_MAX_PROMPT_LEN = 50_000
_MIN_PROMPT_LEN = 1


def moderate_text(
    text: str,
    *,
    allowlist: Optional[List[str]] = None,
    trace_id: Optional[str] = None,
) -> Dict:
    """Run quick local moderation checks over `text`.

    Returns a dict with keys:
      - allowed: bool
      - reasons: list[str]
      - category: highest-severity category or None
      - details: dict (pattern hits etc)
    """
    if allowlist is None:
        allowlist = []

    t = (text or "").lower()

    reasons: List[str] = []
    details: Dict[str, List[Dict[str, str]]] = {"matches": []}

    # length checks
    if len(t) < _MIN_PROMPT_LEN:
        reasons.append("prompt_too_short")
    if len(t) > _MAX_PROMPT_LEN:
        reasons.append("prompt_too_long")

    # PII regex checks
    for name, pat in _PII_PATTERNS.items():
        if pat.search(text):
            reasons.append(f"pii_detected:{name}")
            details["matches"].append({"type": "pii", "name": name})

    # Keyword checks (skip any allowlist tokens)
    for cat, kws in _DISALLOWED.items():
        for kw in kws:
            if kw in t:
                if any(a.lower() in kw for a in allowlist):
                    continue
                reasons.append(f"disallowed_keyword:{cat}:{kw}")
                details["matches"].append(
                    {"type": "keyword", "category": cat, "keyword": kw}
                )

    # Simple heuristic: treat presence of self_harm/illegal/violence as highest severity
    severity = 0
    category = None
    for r in reasons:
        if r.startswith("disallowed_keyword:self_harm"):
            severity = max(severity, 5)
            category = "self_harm"
        if r.startswith("disallowed_keyword:illegal"):
            severity = max(severity, 5)
            category = "illegal"
        if r.startswith("disallowed_keyword:violence"):
            severity = max(severity, 4)
            category = category or "violence"
        if r.startswith("pii_detected"):
            severity = max(severity, 3)
            category = category or "pii"
        if r.startswith("disallowed_keyword:sexual"):
            severity = max(severity, 3)
            category = category or "sexual"
        if r.startswith("disallowed_keyword:hate"):
            severity = max(severity, 4)
            category = category or "hate"

    allowed = len(reasons) == 0

    result = {
        "allowed": allowed,
        "reasons": reasons,
        "category": category,
        "severity": severity,
        "details": details,
    }
    if not allowed:
        audit_trail.record(
            "moderation_block",
            trace_id=trace_id,
            severity="high" if severity >= 4 else "warn",
            payload={
                "category": category,
                "reasons": reasons,
                "text_preview": text[:160],
            },
        )
    return result


def enforce_moderation(
    text: str,
    *,
    allowlist: Optional[List[str]] = None,
    trace_id: Optional[str] = None,
) -> Dict:
    """Convenience wrapper that returns a result or raises ValueError for blocked content.

    Prefer returning structured result so callers can handle and show helpful messages.
    """
    res = moderate_text(text, allowlist=allowlist, trace_id=trace_id)
    return res

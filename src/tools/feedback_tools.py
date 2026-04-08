"""Tools for qualitative feedback: sentiment heuristics and recurring themes."""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

_POS = re.compile(
    r"\b(love|great|good|happy|nice|excited|positive|best|faster|helped|slick|cool)\b",
    re.I,
)
_NEG = re.compile(
    r"\b(crash|failed|error|lag|slow|negative|worried|churn|glitch|blank|worse|threat|unstable|fragile)\b",
    re.I,
)
_THEMES = [
    ("smart_tasks_stability", re.compile(r"smart tasks|crash|rotation|panel|viewcontroller", re.I)),
    ("payments", re.compile(r"payment|billing|charge|refund|bank", re.I)),
    ("latency_api", re.compile(r"latency|api|sluggish|500|server", re.I)),
    ("migration_ux", re.compile(r"migration|shortcuts|confus|docs|onboard", re.I)),
    ("comms_expectations", re.compile(r"marketing|communicat|silent|rollout|pause", re.I)),
]


def summarize_feedback_sentiment(feedback_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Lightweight sentiment mix (keyword-based). Invoked by Marketing/Comms agent.
    """
    logger.info("[TOOL] summarize_feedback_sentiment count=%s", len(feedback_items))
    pos = neg = neu = 0
    for item in feedback_items:
        t = item.get("text", "")
        pc, nc = len(_POS.findall(t)), len(_NEG.findall(t))
        if pc > nc:
            pos += 1
        elif nc > pc:
            neg += 1
        else:
            neu += 1
    total = max(len(feedback_items), 1)
    return {
        "counts": {"positive": pos, "negative": neg, "neutral": neu, "total": len(feedback_items)},
        "ratios": {
            "positive": round(pos / total, 3),
            "negative": round(neg / total, 3),
            "neutral": round(neu / total, 3),
        },
        "headline": f"{neg} negative-leaning / {pos} positive-leaning / {neu} neutral (heuristic)",
    }


def extract_recurring_themes(feedback_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Count theme hits across feedback to surface recurring issues (and some noise).
    Invoked by Marketing/Comms agent.
    """
    logger.info("[TOOL] extract_recurring_themes count=%s", len(feedback_items))
    theme_counts: Counter[str] = Counter()
    exemplars: dict[str, str] = {}
    for item in feedback_items:
        text = item.get("text", "")
        fid = item.get("id", "")
        for name, rx in _THEMES:
            if rx.search(text):
                theme_counts[name] += 1
                exemplars.setdefault(name, f"{fid}: {text[:120]}")

    ranked = theme_counts.most_common()
    return {
        "themes": [{"theme": k, "mentions": v} for k, v in ranked],
        "exemplars": exemplars,
        "top_concern": ranked[0][0] if ranked else "none",
    }

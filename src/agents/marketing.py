from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..tools import extract_recurring_themes, summarize_feedback_sentiment
from .base import AgentReport

logger = logging.getLogger(__name__)


class MarketingCommsAgent:
    agent_id = "marketing_comms"
    role = "Marketing / Comms"

    def run(self, context: dict[str, Any]) -> AgentReport:
        logger.info("[AGENT] %s starting", self.agent_id)
        fb_path = Path(context["feedback_json_path"])
        items = json.loads(fb_path.read_text(encoding="utf-8"))

        tool_calls: list[dict[str, Any]] = []
        sent = summarize_feedback_sentiment(items)
        tool_calls.append({"tool": "summarize_feedback_sentiment", "args": {"count": len(items)}})

        themes = extract_recurring_themes(items)
        tool_calls.append({"tool": "extract_recurring_themes", "args": {"count": len(items)}})

        neg_ratio = sent["ratios"]["negative"]
        top = themes.get("top_concern", "none")
        if neg_ratio >= 0.35 or top == "smart_tasks_stability":
            rec = "external_caution_messaging"
        elif neg_ratio >= 0.25:
            rec = "balanced_messaging"
        else:
            rec = "positive_momentum"

        summary = (
            f"{sent.get('headline', '')}. Dominant theme cluster: {top} "
            f"({len(themes.get('themes', []))} theme buckets hit)."
        )
        logger.info("[AGENT] %s done recommendation=%s", self.agent_id, rec)
        return AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            summary=summary,
            tool_calls=tool_calls,
            evidence={"sentiment": sent, "themes": themes},
            recommendation=rec,
        )

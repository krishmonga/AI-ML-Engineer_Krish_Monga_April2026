from __future__ import annotations

import logging
from typing import Any

from ..tools import evaluate_launch_gates, load_release_notes
from .base import AgentReport

logger = logging.getLogger(__name__)


class ProductManagerAgent:
    agent_id = "product_manager"
    role = "Product Manager"

    def run(self, context: dict[str, Any]) -> AgentReport:
        logger.info("[AGENT] %s starting", self.agent_id)
        notes_path = context["release_notes_path"]
        aggregate = context["data_analyst_aggregate"]

        tool_calls: list[dict[str, Any]] = []
        notes = load_release_notes(notes_path)
        tool_calls.append({"tool": "load_release_notes", "args": {"path": str(notes_path)}})

        latest = aggregate.get("latest_day", {})
        gates = evaluate_launch_gates(latest, aggregate)
        tool_calls.append({"tool": "evaluate_launch_gates", "args": {}})

        if not gates.get("all_pass", False):
            rec = "no_go_gates_failed"
        else:
            rec = "go_if_engineering_confirms"

        failed = gates.get("failed_gates", [])
        funnel_latest = latest.get("feature_funnel_completion_pct")
        summary = (
            f"User-impact framing: latest feature_funnel_completion_pct={funnel_latest}. "
            f"Launch gates: {'PASS' if gates.get('all_pass') else 'FAIL'} "
            f"({len(failed)} failed)."
        )
        logger.info("[AGENT] %s done recommendation=%s", self.agent_id, rec)
        return AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            summary=summary,
            tool_calls=tool_calls,
            evidence={"release_notes_excerpt": notes[:800], "gates": gates},
            recommendation=rec,
        )

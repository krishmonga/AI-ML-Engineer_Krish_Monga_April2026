from __future__ import annotations

import logging
from typing import Any

from ..tools import cross_check_quant_qual_alignment
from .base import AgentReport

logger = logging.getLogger(__name__)


class RiskCriticAgent:
    agent_id = "risk_critic"
    role = "Risk / Critic"

    def run(self, context: dict[str, Any]) -> AgentReport:
        """
        Challenges prior agent outputs without additional tools (optional pattern).
        Assessment allows extra design; critic here uses structured cross-checks only.
        """
        logger.info("[AGENT] %s starting", self.agent_id)
        da = context["reports"]["data_analyst"]
        mk = context["reports"]["marketing_comms"]
        pm = context["reports"]["product_manager"]
        sre = context["reports"].get("sre")

        anomalies = da.evidence.get("anomalies", {})
        flags = anomalies.get("flags", [])
        high_flags = [f for f in flags if f.get("severity") == "high"]

        gates = pm.evidence.get("gates", {})
        gate_fail = not gates.get("all_pass", True)

        neg_ratio = mk.evidence.get("sentiment", {}).get("ratios", {}).get("negative", 0)

        alignment = cross_check_quant_qual_alignment(
            gate_all_pass=gates.get("all_pass", True),
            high_severity_flag_count=len(high_flags),
            negative_feedback_ratio=neg_ratio,
        )

        concerns: list[str] = []
        if gate_fail:
            concerns.append("Explicit launch gates failed on latest day — do not over-index on DAU growth.")
        if len(high_flags) >= 2:
            concerns.append("Multiple high-severity quantitative regressions; variance not explained by seasonality.")
        if neg_ratio >= 0.3:
            concerns.append("Negative-leaning feedback share is elevated; comms must not outpace stability fixes.")
        if sre and sre.evidence.get("health", {}).get("band") == "red":
            concerns.append("SRE health band is red — treat as production incident until score improves.")

        if gate_fail or len(high_flags) >= 2:
            rec = "prefer_pause_or_roll_back"
        elif len(high_flags) == 1 or neg_ratio >= 0.28:
            rec = "prefer_pause_partial_rollout"
        else:
            rec = "proceed_with_monitoring"

        tool_calls: list[dict[str, Any]] = [
            {
                "tool": "cross_check_quant_qual_alignment",
                "args": {
                    "gate_all_pass": gates.get("all_pass", True),
                    "high_severity_flag_count": len(high_flags),
                    "negative_feedback_ratio": neg_ratio,
                },
            }
        ]

        summary = "Cross-functional critique: " + (
            "; ".join(concerns) if concerns else "No major contradictions between qual and quant signals."
        )
        logger.info("[AGENT] %s done recommendation=%s", self.agent_id, rec)
        return AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            summary=summary,
            tool_calls=tool_calls,
            evidence={
                "concerns": concerns,
                "high_flags_count": len(high_flags),
                "alignment_audit": alignment,
            },
            recommendation=rec,
        )

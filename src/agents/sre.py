from __future__ import annotations

import logging
from typing import Any

from ..tools import compute_sre_health_score, propose_incident_readiness_actions
from .base import AgentReport

logger = logging.getLogger(__name__)


class SreAgent:
    agent_id = "sre"
    role = "SRE / Reliability"

    def run(self, context: dict[str, Any]) -> AgentReport:
        logger.info("[AGENT] %s starting", self.agent_id)
        aggregate = context["data_analyst_aggregate"]
        anomalies = context.get("data_analyst_anomalies", {})

        tool_calls: list[dict[str, Any]] = []
        health = compute_sre_health_score(aggregate, anomalies)
        tool_calls.append({"tool": "compute_sre_health_score", "args": {}})

        readiness = propose_incident_readiness_actions(health)
        tool_calls.append({"tool": "propose_incident_readiness_actions", "args": {"band": health.get("band")}})

        rec = "stable" if health["band"] == "green" else "elevated" if health["band"] == "amber" else "critical"
        summary = (
            f"SRE health score={health['score']}/100 ({health['band']}). "
            f"Top factors: {', '.join(health.get('factors', [])[:5]) or 'none'}."
        )
        logger.info("[AGENT] %s done recommendation=%s", self.agent_id, rec)
        return AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            summary=summary,
            tool_calls=tool_calls,
            evidence={"health": health, "readiness": readiness},
            recommendation=rec,
        )

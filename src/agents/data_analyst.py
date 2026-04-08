from __future__ import annotations

import logging
from typing import Any

from ..tools import aggregate_launch_metrics, detect_metric_anomalies
from .base import AgentReport

logger = logging.getLogger(__name__)


class DataAnalystAgent:
    agent_id = "data_analyst"
    role = "Data Analyst"

    def run(self, context: dict[str, Any]) -> AgentReport:
        logger.info("[AGENT] %s starting", self.agent_id)
        metrics_path = context["metrics_csv_path"]

        tool_calls: list[dict[str, Any]] = []
        agg = aggregate_launch_metrics(metrics_path)
        tool_calls.append({"tool": "aggregate_launch_metrics", "args": {"path": str(metrics_path)}})

        anomalies = detect_metric_anomalies(agg)
        tool_calls.append({"tool": "detect_metric_anomalies", "args": {}})

        high = sum(1 for f in anomalies.get("flags", []) if f.get("severity") == "high")
        rec = "pause_or_roll_back" if high >= 2 else "caution" if high == 1 else "healthy_metrics"

        summary = (
            f"Analyzed {agg.get('row_count', 0)} days ({agg.get('date_range', {})}). "
            f"{anomalies.get('summary', '')}."
        )

        logger.info("[AGENT] %s done recommendation=%s", self.agent_id, rec)
        return AgentReport(
            agent_id=self.agent_id,
            role=self.role,
            summary=summary,
            tool_calls=tool_calls,
            evidence={"aggregate": agg, "anomalies": anomalies},
            recommendation=rec,
        )

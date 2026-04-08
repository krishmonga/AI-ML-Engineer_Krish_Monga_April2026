"""SRE / reliability tools: severity scoring and operational follow-ups."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_sre_health_score(
    aggregate: dict[str, Any],
    anomalies: dict[str, Any],
) -> dict[str, Any]:
    """
    Composite 0-100 score (higher = worse) from metric deltas and anomaly flags.
    Invoked by the SRE agent.
    """
    logger.info("[TOOL] compute_sre_health_score")
    score = 0.0
    factors: list[str] = []
    for f in anomalies.get("flags", []):
        sev = f.get("severity", "medium")
        bump = 18 if sev == "high" else 10 if sev == "medium" else 4
        score += bump
        factors.append(f.get("type", "flag"))

    m = aggregate.get("metrics", {})
    crash = m.get("crash_rate_pct", {})
    if crash.get("delta_pct", 0) > 50:
        score += 12
        factors.append("crash_trend_pct")

    pay = m.get("payment_success_pct", {})
    if pay.get("delta_pct", 0) < -0.3:
        score += 15
        factors.append("payment_trend")

    lat = m.get("api_p95_ms", {})
    if lat.get("delta_pct", 0) > 20:
        score += 10
        factors.append("latency_trend")

    score = min(100.0, score)
    band = "green" if score < 25 else "amber" if score < 55 else "red"
    return {
        "score": round(score, 1),
        "band": band,
        "factors": list(dict.fromkeys(factors)),
    }


def propose_incident_readiness_actions(health: dict[str, Any]) -> dict[str, Any]:
    """
    Map health band to concrete SRE actions (telemetry, paging, rollback prep).
    Invoked by the SRE agent.
    """
    logger.info("[TOOL] propose_incident_readiness_actions band=%s", health.get("band"))
    band = health.get("band", "amber")
    if band == "green":
        actions = [
            "Maintain SLO dashboards; no paging policy change.",
            "Sample 1% canary on new build metrics every 6h.",
        ]
    elif band == "amber":
        actions = [
            "Enable paging for crash rate + payment success SLO burn alerts.",
            "Pre-stage rollback runbook + feature flag kill-switch rehearsal.",
            "Increase log sampling on Smart Tasks client surface.",
        ]
    else:
        actions = [
            "Declare incident commander rotation; freeze non-essential deploys.",
            "Shard-level traffic shift + progressive delivery off for hot cells.",
            "Synthetic checks every 5m on payment + core API paths.",
        ]
    return {"band": band, "p0_actions": actions, "owner": "SRE On-Call"}

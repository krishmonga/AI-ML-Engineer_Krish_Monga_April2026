from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agents import (
    AgentReport,
    DataAnalystAgent,
    MarketingCommsAgent,
    ProductManagerAgent,
    RiskCriticAgent,
    SreAgent,
)
from .models import validate_launch_payload

logger = logging.getLogger(__name__)


def _decide(
    reports: dict[str, AgentReport],
) -> tuple[str, list[str], float, list[str]]:
    """
    Coordinator policy: deterministic merge of agent recommendations + gate state.
    Returns decision, key_drivers, confidence 0-1, confidence_boosters.
    """
    da = reports["data_analyst"]
    pm = reports["product_manager"]
    risk = reports["risk_critic"]
    mk = reports["marketing_comms"]

    gates = pm.evidence.get("gates", {})
    failed = gates.get("failed_gates", [])
    failed_names = {f["gate"] for f in failed}

    flags = da.evidence.get("anomalies", {}).get("flags", [])
    high = [f for f in flags if f.get("severity") == "high"]

    neg_ratio = mk.evidence.get("sentiment", {}).get("ratios", {}).get("negative", 0)

    drivers: list[str] = []
    if "crash_gate_breach" in {f.get("type") for f in flags} or "crash_rate_max_pct" in failed_names:
        drivers.append("Crash rate breached launch gate and is trending up (see crash_rate_pct).")
    if "payment_success_min_pct" in failed_names or "payment_success_drift" in {f.get("type") for f in flags}:
        drivers.append("Payment success below gate / declining (see payment_success_pct).")
    if "api_p95_max_regression_ratio" in failed_names:
        drivers.append("API p95 latency regressed beyond 15% vs early-window baseline (release gate).")
    if "support_tickets_max_surge_ratio" in failed_names:
        drivers.append("Support ticket volume exceeded 1.4× baseline vs early window (release gate).")
    if neg_ratio >= 0.28:
        drivers.append(f"Elevated negative-leaning feedback share (~{neg_ratio:.0%} heuristic).")
    if not drivers:
        drivers.append("Signals within acceptable band per synthesized agent review.")

    # Decision tree
    critical_payment = "payment_success_min_pct" in failed_names
    critical_crash = "crash_rate_max_pct" in failed_names
    sre = reports.get("sre")
    sre_red = (
        sre is not None and sre.evidence.get("health", {}).get("band") == "red"
        if sre
        else False
    )
    if critical_payment and critical_crash and len(high) >= 2:
        decision = "Roll Back"
    elif sre_red and critical_crash:
        decision = "Roll Back"
    elif critical_crash or critical_payment or len(high) >= 2:
        decision = "Pause"
    elif risk.recommendation == "prefer_pause_partial_rollout" or len(high) == 1:
        decision = "Pause"
    elif risk.recommendation == "proceed_with_monitoring" and gates.get("all_pass"):
        decision = "Proceed"
    else:
        decision = "Pause"

    boosters = [
        "7-day stable crash rate under gate with no payment regression",
        "Repeated negative theme mentions drop after hotfix",
        "p95 latency returns within 15% of pre-release baseline",
    ]

    confidence = 0.55
    if gates.get("all_pass") and len(high) == 0:
        confidence = 0.78
    elif decision == "Roll Back":
        confidence = 0.72
    elif decision == "Pause":
        confidence = 0.68
    if neg_ratio > 0.35:
        confidence -= 0.05
    confidence = max(0.35, min(0.92, confidence))

    return decision, drivers, confidence, boosters


def _risk_register(reports: dict[str, AgentReport]) -> list[dict[str, str]]:
    da_flags = reports["data_analyst"].evidence.get("anomalies", {}).get("flags", [])
    themes = reports["marketing_comms"].evidence.get("themes", {}).get("themes", [])
    top_theme = themes[0]["theme"] if themes else "general_stability"

    reg = [
        {
            "risk": "Stability regressions on Smart Tasks surface",
            "mitigation": "Hotfix crash + reduce rollout %; daily crash review with mobile lead.",
            "severity": "high",
        },
        {
            "risk": "Payment reliability perception",
            "mitigation": "Incident channel with PSP; proactive retries audit; customer comms template.",
            "severity": "high",
        },
        {
            "risk": f"Narrative drift on recurring theme: {top_theme}",
            "mitigation": "Align external messaging with verified fixes; publish known issues with ETA.",
            "severity": "medium",
        },
    ]
    for f in da_flags[:2]:
        if f.get("type") not in ("crash_regression", "payment_success_drift"):
            reg.append(
                {
                    "risk": f.get("detail", "metric risk")[:200],
                    "mitigation": "Instrument metric owner review; add dashboard alert.",
                    "severity": f.get("severity", "medium"),
                }
            )
    return reg[:6]


def _action_plan(decision: str) -> list[dict[str, str]]:
    base = [
        {
            "action": "Freeze rollout increase; hold current exposure until stability review",
            "owner": "PM + SRE",
            "priority": "P0",
        },
        {
            "action": "Ship targeted crash fix for Smart Tasks; canary 5% before wider ramp",
            "owner": "Mobile Platform",
            "priority": "P0",
        },
        {
            "action": "Payment path deep dive: trace failures, add synthetic checks",
            "owner": "Payments Team",
            "priority": "P0",
        },
        {
            "action": "Update support macros + status page; align comms with verified facts",
            "owner": "Marketing/Comms",
            "priority": "P1",
        },
    ]
    if decision == "Roll Back":
        base.insert(
            0,
            {
                "action": "Execute controlled roll back to prior stable build for affected cohorts",
                "owner": "Release Manager",
                "priority": "P0",
            },
        )
    if decision == "Proceed":
        return [
            {
                "action": "Continue phased rollout with enhanced monitoring (crash, p95, payments)",
                "owner": "SRE",
                "priority": "P1",
            },
            {
                "action": "Publish migration guide for Quick Shortcuts users",
                "owner": "PM + Docs",
                "priority": "P2",
            },
        ]
    return base


def _comms_plan(decision: str, reports: dict[str, AgentReport]) -> dict[str, Any]:
    sent = reports["marketing_comms"].evidence.get("sentiment", {})
    return {
        "internal": (
            f"War-room decision: {decision}. Share quant summary + top themes; "
            "no external promises until engineering confirms ETAs."
        ),
        "external": (
            "Acknowledge reports of stability issues; share that we are prioritizing fixes; "
            "link to status page if incident declared."
            if decision != "Proceed"
            else "Highlight checklist value prop; invite feedback with clear support path."
        ),
        "talking_points": [
            sent.get("headline", ""),
            "We are monitoring crash rate, latency, and payment success against explicit launch gates.",
        ],
    }


def run_war_room(
    metrics_csv_path: str | Path,
    feedback_json_path: str | Path,
    release_notes_path: str | Path,
    *,
    scenario_id: str = "default",
) -> dict[str, Any]:
    """
    Execute agent workflow with explicit handoffs and produce final structured output + trace.
    """
    metrics_csv_path = Path(metrics_csv_path)
    feedback_json_path = Path(feedback_json_path)
    release_notes_path = Path(release_notes_path)

    logger.info(
        "[ORCHESTRATOR] inputs metrics=%s feedback=%s release_notes=%s",
        metrics_csv_path,
        feedback_json_path,
        release_notes_path,
    )

    context: dict[str, Any] = {
        "metrics_csv_path": metrics_csv_path,
        "feedback_json_path": feedback_json_path,
        "release_notes_path": release_notes_path,
    }

    da_agent = DataAnalystAgent()
    sre_agent = SreAgent()
    mk_agent = MarketingCommsAgent()
    pm_agent = ProductManagerAgent()
    risk_agent = RiskCriticAgent()

    logger.info("[ORCHESTRATOR] handoff -> DataAnalystAgent")
    da_report = da_agent.run(context)
    context["data_analyst_aggregate"] = da_report.evidence["aggregate"]
    context["data_analyst_anomalies"] = da_report.evidence.get("anomalies", {})

    logger.info("[ORCHESTRATOR] handoff -> SreAgent")
    sre_report = sre_agent.run(context)

    logger.info("[ORCHESTRATOR] handoff -> MarketingCommsAgent")
    mk_report = mk_agent.run(context)

    logger.info("[ORCHESTRATOR] handoff -> ProductManagerAgent")
    pm_report = pm_agent.run(context)

    reports: dict[str, AgentReport] = {
        "data_analyst": da_report,
        "sre": sre_report,
        "marketing_comms": mk_report,
        "product_manager": pm_report,
    }
    context["reports"] = reports

    logger.info("[ORCHESTRATOR] handoff -> RiskCriticAgent")
    risk_report = risk_agent.run(context)
    reports["risk_critic"] = risk_report

    decision, drivers, confidence, boosters = _decide(reports)

    latest = da_report.evidence["aggregate"].get("latest_day", {})
    themes = mk_report.evidence.get("themes", {})
    sent = mk_report.evidence.get("sentiment", {})

    core: dict[str, Any] = {
        "decision": decision,
        "rationale": {
            "key_drivers": drivers,
            "metric_references": [
                f"latest_day.crash_rate_pct={latest.get('crash_rate_pct')}",
                f"latest_day.payment_success_pct={latest.get('payment_success_pct')}",
                f"latest_day.api_p95_ms={latest.get('api_p95_ms')}",
                f"latest_day.support_tickets={latest.get('support_tickets')}",
            ],
            "feedback_summary": sent.get("headline", ""),
            "top_feedback_themes": themes.get("themes", [])[:5],
        },
        "risk_register": _risk_register(reports),
        "action_plan_24_48h": _action_plan(decision),
        "communication_plan": _comms_plan(decision, reports),
        "confidence": {
            "score": round(confidence, 2),
            "what_would_increase_confidence": boosters,
        },
    }
    validate_launch_payload(core)

    final: dict[str, Any] = {
        **core,
        "trace": {
            "agents": {k: asdict(v) for k, v in reports.items()},
            "coordinator": {
                "policy": "deterministic_merge_v2_sre_full_gates",
                "final_decision": decision,
                "scenario": scenario_id,
            },
        },
    }

    logger.info("[ORCHESTRATOR] FINAL DECISION: %s (confidence=%s)", decision, confidence)
    return final


def save_output(final: dict[str, Any], out_path: Path, fmt: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        out_path.write_text(json.dumps(final, indent=2), encoding="utf-8")
    elif fmt == "yaml":
        import yaml

        out_path.write_text(yaml.safe_dump(final, sort_keys=False, allow_unicode=True), encoding="utf-8")
    else:
        raise ValueError(fmt)
    logger.info("[ORCHESTRATOR] wrote %s", out_path)

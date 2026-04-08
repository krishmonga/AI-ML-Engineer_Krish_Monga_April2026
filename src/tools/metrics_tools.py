"""Tools for quantitative metrics: aggregation and simple anomaly/regression detection."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

logger = logging.getLogger(__name__)


def aggregate_launch_metrics(metrics_csv_path: str | Path) -> dict[str, Any]:
    """
    Load time-series metrics and compute first-half vs second-half trends.
    Invoked by the Data Analyst agent.
    """
    path = Path(metrics_csv_path)
    logger.info("[TOOL] aggregate_launch_metrics path=%s", path)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) < 4:
        return {"error": "insufficient_rows", "row_count": len(rows)}

    numeric_cols = [k for k in rows[0].keys() if k != "date"]

    def parse_row(r: dict[str, str]) -> dict[str, float]:
        out: dict[str, float] = {}
        for k in numeric_cols:
            out[k] = float(r[k])
        return out

    parsed = [parse_row(r) for r in rows]
    mid = len(parsed) // 2
    early, late = parsed[:mid], parsed[mid:]

    def avg_slice(slice_rows: list[dict[str, float]], key: str) -> float:
        return mean(r[key] for r in slice_rows)

    per_metric: dict[str, Any] = {}
    for col in numeric_cols:
        e, l = avg_slice(early, col), avg_slice(late, col)
        delta = l - e
        pct = (delta / e * 100.0) if e else 0.0
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        per_metric[col] = {
            "early_mean": round(e, 4),
            "late_mean": round(l, 4),
            "delta": round(delta, 4),
            "delta_pct": round(pct, 2),
            "direction": direction,
        }

    latest = parsed[-1]
    return {
        "row_count": len(rows),
        "date_range": {"start": rows[0]["date"], "end": rows[-1]["date"]},
        "latest_day": {k: round(latest[k], 4) for k in numeric_cols},
        "metrics": per_metric,
    }


def detect_metric_anomalies(
    aggregate: dict[str, Any],
    *,
    crash_spike_factor: float = 1.5,
    latency_spike_factor: float = 1.15,
) -> dict[str, Any]:
    """
    Flag simple regressions vs early-window baseline and threshold-style anomalies.
    Invoked by the Data Analyst agent.
    """
    logger.info("[TOOL] detect_metric_anomalies")
    flags: list[dict[str, Any]] = []
    if "metrics" not in aggregate:
        return {"flags": [{"type": "error", "detail": aggregate.get("error", "bad aggregate")}]}

    m = aggregate["metrics"]
    latest = aggregate.get("latest_day", {})

    def flag(t: str, detail: str, severity: str, refs: list[str]) -> None:
        flags.append({"type": t, "detail": detail, "severity": severity, "metric_refs": refs})

    # Crash rate: late mean vs early mean
    cr = m.get("crash_rate_pct", {})
    if cr.get("late_mean", 0) > crash_spike_factor * max(cr.get("early_mean", 0), 1e-9):
        flag(
            "crash_regression",
            f"Crash rate late window ({cr.get('late_mean')}) >> early ({cr.get('early_mean')})",
            "high",
            ["crash_rate_pct"],
        )

    # API p95
    lat = m.get("api_p95_ms", {})
    if lat.get("late_mean", 0) > latency_spike_factor * max(lat.get("early_mean", 0), 1e-9):
        flag(
            "latency_regression",
            f"p95 latency late ({lat.get('late_mean')} ms) vs early ({lat.get('early_mean')} ms)",
            "medium",
            ["api_p95_ms"],
        )

    # Payment success downward trend
    pay = m.get("payment_success_pct", {})
    if pay.get("delta_pct", 0) < -0.5:
        flag(
            "payment_success_drift",
            f"Payment success declining: Δ%={pay.get('delta_pct')}",
            "high",
            ["payment_success_pct"],
        )

    # Support tickets upward
    sup = m.get("support_tickets", {})
    if sup.get("delta_pct", 0) > 40:
        flag(
            "support_volume_spike",
            f"Support tickets rising: Δ%={sup.get('delta_pct')}",
            "medium",
            ["support_tickets"],
        )

    # Churn uptick
    ch = m.get("churn_rate_pct", {})
    if ch.get("delta_pct", 0) > 30:
        flag(
            "churn_increase",
            f"Churn rate rising: Δ%={ch.get('delta_pct')}",
            "high",
            ["churn_rate_pct"],
        )

    # Latest-day crash vs gate-style threshold (0.12% from release notes context)
    if latest.get("crash_rate_pct", 0) > 0.12:
        flag(
            "crash_gate_breach",
            f"Latest crash_rate_pct={latest.get('crash_rate_pct')} exceeds 0.12% gate",
            "high",
            ["crash_rate_pct"],
        )

    return {
        "flags": flags,
        "summary": f"{len(flags)} anomaly/regression signal(s)",
    }

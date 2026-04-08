"""Tools tied to release criteria and known-issue context."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_release_notes(release_notes_path: str | Path) -> str:
    """Read release notes for PM / Risk context."""
    path = Path(release_notes_path)
    logger.info("[TOOL] load_release_notes path=%s", path)
    return path.read_text(encoding="utf-8")


def evaluate_launch_gates(latest_day: dict[str, float], aggregate: dict[str, Any]) -> dict[str, Any]:
    """
    All success criteria from ``data/release_notes.md``:
    - Crash rate ≤ 0.12%
    - API p95 latency ≤ 15% regression vs early-window baseline
    - Payment success ≥ 98.5%
    - Support tickets ≤ 1.4× early-window baseline (late window mean)
    """
    logger.info("[TOOL] evaluate_launch_gates")
    metrics = aggregate.get("metrics", {})
    early_p95 = metrics.get("api_p95_ms", {}).get("early_mean")
    late_p95 = metrics.get("api_p95_ms", {}).get("late_mean")
    early_tix = metrics.get("support_tickets", {}).get("early_mean")
    late_tix = metrics.get("support_tickets", {}).get("late_mean")

    p95_ratio = (late_p95 / early_p95) if early_p95 else 1.0
    p95_ok = p95_ratio <= 1.15 if early_p95 else True

    tix_ratio = (late_tix / early_tix) if early_tix else 1.0
    tix_ok = tix_ratio <= 1.4 if early_tix else True

    gates = [
        {
            "name": "crash_rate_max_pct",
            "threshold": 0.12,
            "actual": latest_day.get("crash_rate_pct"),
            "cmp": "le",
        },
        {
            "name": "payment_success_min_pct",
            "threshold": 98.5,
            "actual": latest_day.get("payment_success_pct"),
            "cmp": "ge",
        },
        {
            "name": "api_p95_max_regression_ratio",
            "threshold": 1.15,
            "actual": round(p95_ratio, 4),
            "cmp": "le",
            "detail": f"late_mean={late_p95} vs early_mean={early_p95}",
        },
        {
            "name": "support_tickets_max_surge_ratio",
            "threshold": 1.4,
            "actual": round(tix_ratio, 4),
            "cmp": "le",
            "detail": f"late_mean={late_tix} vs early_mean={early_tix}",
        },
    ]

    results = []
    for g in gates:
        actual = g["actual"]
        th = g["threshold"]
        if actual is None:
            status = "unknown"
        elif g["cmp"] == "le":
            status = "pass" if actual <= th else "fail"
        else:
            status = "pass" if actual >= th else "fail"
        results.append(
            {
                "gate": g["name"],
                "threshold": th,
                "actual": actual,
                "status": status,
                **({"detail": g["detail"]} if "detail" in g else {}),
            }
        )

    failed = [r for r in results if r["status"] == "fail"]
    return {
        "gate_results": results,
        "all_pass": len(failed) == 0,
        "failed_gates": failed,
    }

"""Cross-checks between qualitative and quantitative agent outputs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def cross_check_quant_qual_alignment(
    *,
    gate_all_pass: bool,
    high_severity_flag_count: int,
    negative_feedback_ratio: float,
) -> dict[str, Any]:
    """
    Sanity-check whether narrative risk matches metrics. Invoked by Risk/Critic agent.
    """
    logger.info("[TOOL] cross_check_quant_qual_alignment")
    contradictions: list[str] = []
    if gate_all_pass and high_severity_flag_count >= 2:
        contradictions.append("Gates pass but multiple high-severity metric flags — verify gate thresholds.")
    if not gate_all_pass and negative_feedback_ratio < 0.15:
        contradictions.append("Gates fail while feedback looks calm — possible reporting delay or cohort skew.")

    aligned = len(contradictions) == 0
    return {
        "aligned": aligned,
        "contradictions": contradictions,
        "summary": "aligned" if aligned else "potential_misalignment",
    }

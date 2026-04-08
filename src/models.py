"""Validated contract for the final launch decision document (no LLM required)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CommunicationPlanModel(BaseModel):
    internal: str
    external: str
    talking_points: list[str]


class ConfidenceModel(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    what_would_increase_confidence: list[str]


class LaunchDecisionPayload(BaseModel):
    """Required structured output from the brief (trace added separately)."""

    decision: Literal["Proceed", "Pause", "Roll Back"]
    rationale: dict[str, Any]
    risk_register: list[dict[str, Any]]
    action_plan_24_48h: list[dict[str, Any]]
    communication_plan: CommunicationPlanModel
    confidence: ConfidenceModel


def validate_launch_payload(payload: dict[str, Any]) -> LaunchDecisionPayload:
    # Pydantic v2: model_validate; v1: parse_obj
    fn = getattr(LaunchDecisionPayload, "model_validate", None)
    if fn is not None:
        return fn(payload)
    return LaunchDecisionPayload.parse_obj(payload)  # type: ignore[no-any-return,union-attr]


def launch_payload_json_schema() -> dict[str, Any]:
    fn = getattr(LaunchDecisionPayload, "model_json_schema", None)
    if fn is not None:
        return fn()
    return LaunchDecisionPayload.schema()  # type: ignore[no-any-return,union-attr]

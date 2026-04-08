from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentReport:
    """Structured handoff from an agent to the orchestrator."""

    agent_id: str
    role: str
    summary: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

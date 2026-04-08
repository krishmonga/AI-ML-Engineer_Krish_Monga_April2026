"""Named scenario packs (metrics + feedback + release notes) for demos and regression checks."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class ScenarioPaths(NamedTuple):
    metrics: Path
    feedback: Path
    release_notes: Path


def resolve_scenario(root: Path, scenario: str) -> tuple[ScenarioPaths, str]:
    """
    Map CLI scenario id to input paths.
    ``default`` uses top-level ``data/`` (original red-team trajectory).
    """
    s = scenario.strip().lower()
    if s in ("default", "red"):
        return (
            ScenarioPaths(
                metrics=root / "data" / "metrics.csv",
                feedback=root / "data" / "feedback.json",
                release_notes=root / "data" / "release_notes.md",
            ),
            "red" if s == "red" else "default",
        )
    folder = root / "data" / "scenarios" / s
    return (
        ScenarioPaths(
            metrics=folder / "metrics.csv",
            feedback=folder / "feedback.json",
            release_notes=folder / "release_notes.md",
        ),
        s,
    )

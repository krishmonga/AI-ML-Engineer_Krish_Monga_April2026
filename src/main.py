"""
CLI entry: run the launch war room end-to-end.

Usage (from repo root):
    python -m src.main
    python -m src.main --scenario green --html outputs/dossier.html
    python -m src.main --export-schema outputs/launch_decision.schema.json --schema-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .models import launch_payload_json_schema
from .orchestrator import run_war_room, save_output
from .report_html import write_war_room_html
from .scenarios import resolve_scenario


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    root = _project_root()
    default_out = root / "outputs" / "launch_decision.json"

    p = argparse.ArgumentParser(description="PurpleMerit Assessment 1 — Launch War Room")
    p.add_argument(
        "--scenario",
        default="default",
        help="Input pack: default|red (data/), green, amber (data/scenarios/<name>/)",
    )
    p.add_argument("--metrics", type=Path, default=None, help="Override metrics CSV path")
    p.add_argument("--feedback", type=Path, default=None, help="Override feedback JSON path")
    p.add_argument("--release-notes", type=Path, default=None, help="Override release notes path")
    p.add_argument("--output", type=Path, default=default_out, help="Structured output file path")
    p.add_argument("--format", choices=("json", "yaml"), default="json")
    p.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Also write a self-contained HTML dossier (charts + gate table + agent timeline)",
    )
    p.add_argument(
        "--export-schema",
        type=Path,
        default=None,
        help="Write JSON Schema for the final payload (excluding trace)",
    )
    p.add_argument(
        "--schema-only",
        action="store_true",
        help="With --export-schema, write schema and exit (no war room run)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    args = p.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.schema_only and args.export_schema is None:
        p.error("--schema-only requires --export-schema")

    if args.export_schema is not None:
        args.export_schema.parent.mkdir(parents=True, exist_ok=True)
        args.export_schema.write_text(
            json.dumps(launch_payload_json_schema(), indent=2),
            encoding="utf-8",
        )
        logging.info("Wrote JSON Schema to %s", args.export_schema)
        if args.schema_only:
            return 0

    paths, scenario_key = resolve_scenario(root, args.scenario)
    metrics = args.metrics or paths.metrics
    feedback = args.feedback or paths.feedback
    release_notes = args.release_notes or paths.release_notes

    for path, label in (
        (metrics, "metrics"),
        (feedback, "feedback"),
        (release_notes, "release notes"),
    ):
        if not path.exists():
            logging.error("Missing %s file: %s", label, path)
            return 1

    if args.format == "yaml" and not str(args.output).endswith((".yaml", ".yml")):
        args.output = args.output.with_suffix(".yaml")

    final = run_war_room(
        metrics,
        feedback,
        release_notes,
        scenario_id=scenario_key,
    )
    save_output(final, args.output, args.format)

    if args.html is not None:
        write_war_room_html(final, metrics, args.html, scenario_label=args.scenario)
        logging.info("Wrote HTML dossier to %s", args.html)

    console_payload = {k: v for k, v in final.items() if k != "trace"}
    if args.format == "yaml":
        import yaml

        print(yaml.safe_dump(console_payload, sort_keys=False, allow_unicode=True))
    else:
        print(json.dumps(console_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

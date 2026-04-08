"""Self-contained HTML war-room dossier (no CDN; open locally for demos)."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def _series_from_csv(metrics_csv: Path, column: str) -> tuple[list[str], list[float]]:
    with metrics_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dates = [r["date"] for r in rows]
    vals = [float(r[column]) for r in rows]
    return dates, vals


def _svg_sparkline(values: list[float], width: int = 640, height: int = 120, color: str = "#a78bfa") -> str:
    if not values:
        return ""
    vmin, vmax = min(values), max(values)
    span = (vmax - vmin) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = (i / max(n - 1, 1)) * (width - 20) + 10
        y = height - 10 - ((v - vmin) / span) * (height - 20)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="sparkline"><polyline fill="none" stroke="{color}" '
        f'stroke-width="2" points="{poly}" /></svg>'
    )


def write_war_room_html(
    final: dict[str, Any],
    metrics_csv: Path,
    out_html: Path,
    *,
    scenario_label: str,
) -> None:
    dates, crash = _series_from_csv(metrics_csv, "crash_rate_pct")
    _, p95 = _series_from_csv(metrics_csv, "api_p95_ms")

    decision = html.escape(str(final.get("decision", "")))
    conf = final.get("confidence", {})
    score = conf.get("score", 0)

    rationale = final.get("rationale", {})
    drivers = rationale.get("key_drivers", [])
    drivers_li = "".join(f"<li>{html.escape(str(d))}</li>" for d in drivers)

    trace = final.get("trace", {})
    agents = trace.get("agents", {})
    timeline_rows = []
    order = ["data_analyst", "sre", "marketing_comms", "product_manager", "risk_critic"]
    for i, aid in enumerate(order):
        rep = agents.get(aid)
        if not rep:
            continue
        role = html.escape(str(rep.get("role", aid)))
        summary = html.escape(str(rep.get("summary", ""))[:220])
        tools = rep.get("tool_calls") or []
        tc = ", ".join(html.escape(str(t.get("tool"))) for t in tools)
        timeline_rows.append(
            f"<tr><td>{i + 1}</td><td><strong>{role}</strong></td>"
            f"<td class='muted'>{tc}</td><td>{summary}</td></tr>"
        )

    gates = (
        agents.get("product_manager", {})
        .get("evidence", {})
        .get("gates", {})
        .get("gate_results", [])
    )
    gate_rows = []
    for g in gates:
        st = g.get("status", "")
        cls = "pass" if st == "pass" else "fail" if st == "fail" else ""
        gate_rows.append(
            "<tr>"
            f"<td>{html.escape(str(g.get('gate','')))}</td>"
            f"<td>{html.escape(str(g.get('threshold','')))}</td>"
            f"<td>{html.escape(str(g.get('actual','')))}</td>"
            f"<td class='{cls}'>{html.escape(st)}</td>"
            "</tr>"
        )

    payload_json = json.dumps({k: v for k, v in final.items() if k != "trace"}, indent=2)
    payload_json_esc = html.escape(payload_json)

    crash_svg = _svg_sparkline(crash, color="#f472b6")
    p95_svg = _svg_sparkline(p95, color="#38bdf8")
    x_labels = ", ".join(html.escape(d[5:]) for d in dates[::3])

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Launch War Room — {decision}</title>
  <style>
    :root {{
      --bg: #0c0a14;
      --card: #161225;
      --text: #e8e4ff;
      --muted: #9b92c9;
      --accent: #8b5cf6;
      --pass: #34d399;
      --fail: #fb7185;
    }}
    body {{
      margin: 0; font-family: ui-sans-serif, system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 20% -10%, #2e1064 0%, var(--bg) 55%);
      color: var(--text);
      line-height: 1.5;
    }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    header {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 1rem; margin-bottom: 1.5rem; }}
    h1 {{ font-size: 1.5rem; margin: 0; letter-spacing: -0.02em; }}
    .badge {{
      display: inline-block; padding: 0.35rem 0.75rem; border-radius: 999px;
      font-weight: 600; font-size: 0.85rem;
      background: rgba(139, 92, 246, 0.25); border: 1px solid rgba(139, 92, 246, 0.5);
    }}
    .scenario {{ color: var(--muted); font-size: 0.9rem; }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .card {{
      background: var(--card); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px; padding: 1rem 1.1rem;
      box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    }}
    h2 {{ font-size: 1rem; margin: 0 0 0.75rem; color: var(--muted); font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.35rem; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 500; }}
    .pass {{ color: var(--pass); font-weight: 600; }}
    .fail {{ color: var(--fail); font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 0.82rem; }}
    pre {{
      margin: 0; padding: 1rem; border-radius: 12px;
      background: #0f172a; border: 1px solid rgba(255,255,255,0.08);
      overflow: auto; max-height: 420px; font-size: 0.75rem; color: #cbd5e1;
    }}
    ul {{ margin: 0.25rem 0 0 1rem; }}
    .foot {{ margin-top: 2rem; font-size: 0.8rem; color: var(--muted); }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Launch war room dossier</h1>
      <span class="badge">Decision: {decision}</span>
      <span class="scenario">Scenario: {html.escape(scenario_label)} · confidence {html.escape(str(score))}</span>
    </header>

    <div class="grid">
      <div class="card">
        <h2>Crash rate (%)</h2>
        {crash_svg}
        <p class="muted">Dates (sample): {x_labels}</p>
      </div>
      <div class="card">
        <h2>API p95 latency (ms)</h2>
        {p95_svg}
        <p class="muted">Same window as metrics CSV</p>
      </div>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Launch gates (Product Manager tool output)</h2>
      <table>
        <thead><tr><th>Gate</th><th>Threshold</th><th>Actual</th><th>Status</th></tr></thead>
        <tbody>{"".join(gate_rows) or "<tr><td colspan='4' class='muted'>No gate data</td></tr>"}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Rationale (key drivers)</h2>
      <ul>{drivers_li or "<li class='muted'>—</li>"}</ul>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Agent timeline &amp; tool calls</h2>
      <table>
        <thead><tr><th>#</th><th>Agent</th><th>Tools</th><th>Summary</th></tr></thead>
        <tbody>{"".join(timeline_rows)}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Structured output (JSON)</h2>
      <pre>{payload_json_esc}</pre>
    </div>

    <p class="foot">
      Generated locally for PurpleMerit Assessment 1. Open this file in a browser — no network required.
    </p>
  </div>
</body>
</html>"""

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(doc, encoding="utf-8")

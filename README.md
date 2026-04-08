# AI/ML Engineer Assessment — Launch War Room (Assessment 1)

Multi-agent launch “war room”: **mock dashboard** inputs (metrics CSV, feedback JSON, release notes), **five specialized agents** that **invoke real tools**, and a **validated** structured decision (**Proceed / Pause / Roll Back**) with rationale, risk register, 24–48h action plan, communication plan, and confidence. **No LLM required**; **UI optional** per brief — this repo adds an **optional offline HTML dossier** for demos.

## What makes this submission stand out

- **Extra agent:** **SRE / Reliability** (after Data Analyst) with `compute_sre_health_score` and `propose_incident_readiness_actions`.
- **Release gates match the doc:** all four criteria in `data/release_notes.md` are enforced in code — crash cap, **p95 ≤15% regression vs early window**, payment floor, **support tickets ≤1.4× early window** (`evaluate_launch_gates`).
- **Scenario packs:** `green` → **Proceed**, `amber` → **Pause** (support surge), `default`/`red` → **Roll Back** — shows the system is not single-outcome.
- **Contract validation:** Pydantic **`LaunchDecisionPayload`** validates the final document before writing; **`--export-schema`** emits JSON Schema (works with Pydantic v1 or v2).
- **HTML war-room dossier (offline):** `--html outputs/war_room_dossier.html` — sparklines for crash + p95, gate table, agent timeline with tool names, embedded JSON. **No CDN;** open in a browser for a strong demo reel.

## Repository layout

```
purplemerit/
├── README.md
├── requirements.txt          # pyyaml, pydantic (v1 or v2)
├── data/
│   ├── metrics.csv             # default “red” trajectory
│   ├── feedback.json
│   ├── release_notes.md
│   └── scenarios/
│       ├── green/              # Proceed path
│       └── amber/              # Pause path (support gate breach)
├── src/
│   ├── main.py
│   ├── orchestrator.py
│   ├── models.py               # payload validation + schema export
│   ├── scenarios.py
│   ├── report_html.py          # self-contained HTML report
│   ├── agents/                 # PM, Data, Marketing, SRE, Risk
│   └── tools/
└── outputs/                    # generated (json may be gitignored)
```

## Agents and orchestration flow

1. **Data Analyst** → `aggregate_launch_metrics`, `detect_metric_anomalies`
2. **SRE** → `compute_sre_health_score`, `propose_incident_readiness_actions`
3. **Marketing / Comms** → `summarize_feedback_sentiment`, `extract_recurring_themes`
4. **Product Manager** → `load_release_notes`, `evaluate_launch_gates` (full four gates + aggregate)
5. **Risk / Critic** → `cross_check_quant_qual_alignment` (and SRE band awareness)
6. **Coordinator** merges into the final JSON/YAML (`deterministic_merge_v2_sre_full_gates`).

**Traceability:** `[ORCHESTRATOR]` / `[AGENT]` / `[TOOL]` logs; `trace` in the output file.

## Setup

**Python:** 3.10+ recommended.

```bash
cd /path/to/purplemerit
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On Debian/Ubuntu, if `venv` fails, install `python3-venv` / `python3-full`, or use a venv tool you prefer.

## Run

**Default (red) scenario:**

```bash
python -m src.main
```

**Green / amber packs:**

```bash
python -m src.main --scenario green
python -m src.main --scenario amber
```

**HTML dossier + JSON (great for the demo video):**

```bash
python -m src.main --scenario green --html outputs/war_room_dossier.html --output outputs/launch_decision.json
```

**YAML:**

```bash
python -m src.main --format yaml --output outputs/launch_decision.yaml
```

**JSON Schema for the payload (no `trace`):**

```bash
python -m src.main --export-schema outputs/launch_decision.schema.json --schema-only
```

**Custom inputs** (overrides scenario paths):

```bash
python -m src.main --metrics path/to/metrics.csv --feedback path/to/feedback.json --release-notes path/to/release_notes.md
```

## Environment variables

No API keys required for the baseline. If you add an LLM later, use env vars only — see `.env.example`.

## Submission checklist (per brief)

- [x] Mock dashboard: metrics + feedback + release notes  
- [x] Required agents + coordinator + **extra SRE agent**  
- [x] ≥2 tools (many more)  
- [x] Structured output + **schema / validation**  
- [x] Logs / trace  

## License

Submitted as part of a hiring assessment for PurpleMerit.

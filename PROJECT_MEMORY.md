# Project Memory: SeaShield AI

> Maintained by the project-memory skill and loaded at every session start.
> Read this first; open other files only when a task needs them.

**Last updated:** 2026-11-14 (Phase 0 complete)
**Repo:** https://github.com/tahabenissa/hackathon-sea (private, branch main)
**Root:** D:\hackthon_sea

## What this project is
SeaShield AI is a HackGlobal 2026 hackathon project (theme: Artificial Intelligence). It is a "trust engine" that detects False Data Injection (FDI) attacks on ocean-buoy data before that data can trigger or suppress maritime alerts. It has four layers: a crypto gate (HMAC, seq, timestamp, nonce), physics checks, ML anomaly detection (Isolation Forest), and cross-buoy validation, all feeding a fusion verdict. Deployment target: Vultr, with $200 in credits (hard budget). The user wants an ambitious, high-quality project.

## Stack and tools
Python 3.12 (pydantic v2, pydantic-settings, paho-mqtt v2, FastAPI, SQLAlchemy 2, psycopg 3, scikit-learn, pandas, httpx), Mosquitto 2, PostgreSQL 16, React 18 + Vite 8.3.8 + React Router 7.18.5 + TS + Leaflet + Recharts (npm audit: 0 vulns), Caddy 2 (HTTPS + reverse proxy), Docker Compose. Dev machine: Windows 11 with Python 3.12.10, Node 24, Docker 29 and git installed. Data: NOAA NDBC stdmet.

## How to build / run / test
- `python -m venv .venv` → `.venv\Scripts\activate` → `pip install -e ".[dev]"`
- `python infra/scripts/gen_buoy_keys.py` → secrets/buoy_keys.json
- `pytest` → 23 passed; `ruff check .` → clean (a global ruff config also enables BLE/FURB rules)
- API: `uvicorn seashield.api.main:app --reload` (docs at /api/docs)
- Dashboard: `cd dashboard && npm install && npm run dev`
- Full stack: `cp .env.example .env` → `docker compose up -d --build` (attacker: `--profile demo`)

## File map
- `SEASHIELD_AI_MASTER_PROMPT.md`: master spec (threat model, architecture, scenarios, Vultr plan)
- `docs/PLAN.md`: **detailed step-by-step plan, phases 0–10**, risks, priority cut list, budget tracker, checklist
- `docs/PHASE_0.md`: Phase 0 report (what was done, results, setup on another machine)
- `.gitattributes`: forces LF line endings (scripts and configs run on Linux)
- `tests/test_api.py`: API + WebSocket smoke tests
- `docs/architecture.md`, `docs/threat-model.md`, `docs/evaluation.md` (empty until Phase 6), `docs/decisions/0001,0002`
- `pyproject.toml`, `Dockerfile` (one image for all Python services), `docker-compose.yml`, `.env.example`, `.gitignore`, `.dockerignore`
- `config/buoys.yaml`: SS-B01..B04 (NDBC station and lat/lon still null, filled in Phase 1)
- `seashield/config.py`: Settings (env prefix SEASHIELD_)
- `seashield/common/`: `schema.py` (Measurements, Telemetry, Verdict, Evidence, Assessment), `signing.py` (HMAC canonical JSON), `registry.py`, `mqtt.py`
- `seashield/engine/`: `crypto_gate.py` ✅, `physics.py` ✅ (heuristic thresholds), `fusion.py` ✅, `baseline.py` ✅ (naive >6 m alert), `pipeline.py` ✅, `anomaly.py` (stub), `spatial.py` (stub + haversine), `__main__.py` (MQTT consumer)
- `seashield/simulator/`: `buoy.py` ✅ (VirtualBuoy signs messages), `replay.py` (stub), `__main__.py`
- `seashield/attacker/`: `scenarios.py` ✅ (tamper, replay, compromised_spike, false_wind, suppress, drift), `__main__.py` (stub CLI)
- `seashield/api/`: `main.py`, `db.py`, `ws.py`, `routes/` (health, buoys, measurements, incidents, alerts, attacks; mostly stubs)
- `ml/`: `download_ndbc.py` ✅, `clean.py`/`features.py`/`train.py`/`evaluate.py` (stubs), `README.md`
- `infra/`: mosquitto (dev conf, prod TLS conf, acl), `caddy/Caddyfile`, `postgres/init.sql` (buoys, measurements, incidents, alerts), `scripts/` (gen_buoy_keys.py, gen_certs.sh, server_setup.sh)
- `dashboard/`: Vite React app; `src/App.tsx` (8 routes), `src/pages/*` (placeholders, Overview calls /api/health), `src/api/client.ts`, `src/styles/theme.css`, Dockerfile (build context = repo root)
- `tests/`: conftest, test_signing, test_crypto_gate, test_physics, test_pipeline
- `seashield_concept.png`, `HackGlobal2026_Badge_B9D470.png`, `new.webp`: images

## Key concepts and decisions
- Crypto proves origin and integrity, not truth. Physics, ML, and neighbour checks cover compromised buoys (T4).
- Verdicts: TRUSTED / REJECTED / SUSPECTED_FDI / CONFIRMED_EVENT / SUPPRESSED_WARNING. Data is never deleted; a human reviews held alerts; escalate when a hidden danger is suspected.
- Verify the signature on the RAW parsed dict, never on a re-serialized model.
- `ts` = send time (now), not historical time. Attack ground truth is logged outside the message.
- Engine writes the DB; the API reads the DB and streams MQTT verdicts over WebSocket (planned, Phase 7).
- One Vultr VPS (2 vCPU/4 GB, ~$20–24/mo, verify). No resource is created without user approval; a stopped instance is still billed.

## Current status
Phase 0 done: `.venv` installed, `secrets/buoy_keys.json` and `.env` (random DB password) created locally (git-ignored), 23 tests pass, dashboard builds, private repo pushed. No data, no model, no cloud resources ($0 spent).

## Next steps
1. Phase 1: choose an NDBC cluster with a real storm; fill config/buoys.yaml; download + implement clean.py (add pyarrow)
2. Phase 2: replay.py + fix seq reset on simulator restart (start from time-based value)

## Gotchas
- NDBC missing values are coded 99/999/9999.
- A large multi-heredoc Bash command failed to parse in this environment; use the Write tool for files.
- Run Python through `.venv/Scripts/python` from the shell; `.env` uses Docker hostnames (set MQTT host to localhost for native runs).
- VirtualBuoy seq starts at 0, so a restart triggers replay rejection (fix planned in Phase 2).

## Session log
- 2026-11-14: Phase 0 done: env, keys, .env, lint fixes, test_api, npm major upgrades (0 vulns), node:22 + npm ci, .gitattributes, private repo hackathon-sea pushed; report in docs/PHASE_0.md.
- 2026-11-14: Built the full project skeleton (Python package, infra, dashboard, tests, docs) and wrote docs/PLAN.md.
- 2026-11-14: Created the master prompt and memory file.

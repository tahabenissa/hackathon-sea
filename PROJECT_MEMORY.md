# Project Memory: SeaShield AI

> Maintained by the project-memory skill and loaded at every session start.
> Read this first; open other files only when a task needs them.

**Last updated:** 2026-11-14 (Phase 2 complete, committed 8aa43a8; config.py has `topic_control_reset`; amqtt is in the dev extras)
**Repo:** https://github.com/tahabenissa/hackathon-sea (private, branch main)
**Root:** D:\hackthon_sea

## What this project is
SeaShield AI is a HackGlobal 2026 hackathon project (theme: Artificial Intelligence). It is a "trust engine" that detects False Data Injection (FDI) attacks on ocean-buoy data before that data can trigger or suppress maritime alerts. It has four layers: a crypto gate (HMAC, seq, timestamp, nonce), physics checks, ML anomaly detection (Isolation Forest), and cross-buoy validation, all feeding a fusion verdict. Deployment target: Vultr, with $200 in credits (hard budget). The user wants an ambitious, high-quality project.

## Hackathon requirements (from the user, 2026-11-15)
- **Submissions close 15 November 2026** (on Vultr Community). Exact hour/timezone: ask the user.
- Tracks: Agentic/GenAI, Multimodal/accessibility, Grounded knowledge/RAG, **Civic and real-world impact** (best fit for SeaShield: a "misinformation checker" for ocean sensors that protects coastal communities).
- Deliverables: PUBLIC GitHub repo with setup + docs; backend on a Vultr Compute instance; recorded demo video running on Vultr; PUBLIC demo URL with a product-style experience; use case + system design with diagrams and screenshots of the user flow.
- Judging: Merit (idea, build, fit) · Reach (real users, shares, votes; talk to users in 3+ countries) · Bonus (cross-university teams, community challenges).

## Stack and tools
Python 3.12 (pydantic v2, pydantic-settings, paho-mqtt v2, FastAPI, SQLAlchemy 2, psycopg 3, scikit-learn, pandas 3, pyarrow, httpx; matplotlib in the `ml` extra), Mosquitto 2, PostgreSQL 16, React 18 + Vite 8.3.8 + React Router 7.18.5 + TS + Leaflet + Recharts (npm audit: 0 vulns), Caddy 2 (HTTPS + reverse proxy), Docker Compose. Dev machine: Windows 11 with Python 3.12.10, Node 24, Docker 29 and git installed. Data: NOAA NDBC stdmet.

## How to build / run / test
- `python -m venv .venv` → `.venv\Scripts\activate` → `pip install -e ".[dev,ml]"`
- `python infra/scripts/gen_buoy_keys.py` → secrets/buoy_keys.json
- Data: `python ml/download_ndbc.py <st> 2023 2024 2025` → `python ml/clean.py 42036 42097 42099 42013` → `python ml/explore.py`
- Live network without Docker: `amqtt -c infra/dev/amqtt.yaml` | `$env:SEASHIELD_MQTT_HOST="localhost"; python -m seashield.engine` | `python -m seashield.simulator --start 2024-09-25T12:00 --end 2024-09-27T12:00 --interval 1` (add `--reset` when jumping back in time)
- `pytest` → 41 passed; `ruff check .` → clean (a global ruff config also enables BLE/FURB rules)
- API: `uvicorn seashield.api.main:app --reload` (docs at /api/docs)
- Dashboard: `cd dashboard && npm install && npm run dev`
- Full stack: `cp .env.example .env` → `docker compose up -d --build` (attacker: `--profile demo`)

## File map
- `SEASHIELD_AI_MASTER_PROMPT.md`: master spec (threat model, architecture, scenarios, Vultr plan)
- `docs/PLAN.md`: **detailed step-by-step plan, phases 0–10**, risks, priority cut list, budget tracker, checklist
- `docs/PHASE_0.md`, `PHASE_1.md`, `PHASE_2.md`: phase reports (what was done, results)
- `docs/data-notes.md`: **all real data facts** (cluster, coverage, outages, storms, neighbour stats, change rates, split)
- `docs/assets/phase1/`: stats.json + figures (normal week, Idalia, Helene, Milton, wave vs wind)
- `.gitattributes`: forces LF line endings (scripts and configs run on Linux)
- `tests/test_api.py`: API + WebSocket smoke tests
- `docs/architecture.md`, `docs/threat-model.md`, `docs/evaluation.md` (empty until Phase 6), `docs/decisions/0001,0002,0003` (0003 = cluster, observed_at, split)
- `pyproject.toml`, `Dockerfile` (one image for all Python services), `docker-compose.yml`, `.env.example`, `.gitignore`, `.dockerignore`
- `config/buoys.yaml`: SS-B01=42036 West Tampa (all sensors), SS-B02=42097 Pulley Ridge (waves), SS-B03=42099 St. Petersburg (waves), SS-B04=42013 C10 (wind/pressure); lat/lon + `sensors`
- `seashield/config.py`: Settings (env prefix SEASHIELD_)
- `seashield/common/`: `schema.py` (Measurements, Telemetry with `ts` + `observed_at`, Verdict, Evidence, Assessment), `signing.py` (HMAC canonical JSON), `registry.py` (Buoy has a `sensors` tuple), `mqtt.py` (`make_client`, `connect_with_retry`)
- `seashield/engine/`: `crypto_gate.py` ✅, `physics.py` ✅ (uses observed_at; per-hour limits from real data: wave 3.5 m/h, wind 15, pressure 20, temp 3; observed_at must increase and be ≤ ts+120 s), `fusion.py` ✅, `baseline.py` ✅ (naive >6 m alert), `pipeline.py` ✅ (+ `reset_history()`), `anomaly.py` (stub), `spatial.py` (stub + haversine), `__main__.py` (MQTT consumer, verdicts → `seashield/verdicts/<id>`, operator reset on `seashield/control/reset`, totals log)
- `seashield/simulator/`: `buoy.py` ✅ (VirtualBuoy; seq = max(prev+1, now µs), restart-safe), `replay.py` ✅ (shared historical clock, own sensors only, empty hour = no message), `__main__.py` ✅ (`--start --end --interval --hours --reset`)
- `infra/dev/amqtt.yaml`: pure-Python dev broker on 127.0.0.1:1883 (Docker blocked locally)
- `seashield/attacker/`: `scenarios.py` ✅ (tamper, replay, compromised_spike, false_wind, suppress, drift), `__main__.py` (stub CLI)
- `seashield/api/`: `main.py`, `db.py`, `ws.py`, `routes/` (health, buoys, measurements, incidents, alerts, attacks; mostly stubs)
- `ml/`: `download_ndbc.py` ✅, `clean.py` ✅ (per-column sentinels, hourly, vector wind dir, `interpolate_short_gaps`), `survey.py` ✅ (compare stations), `explore.py` ✅ (stats + figures), `features.py`/`train.py`/`evaluate.py` (stubs), `README.md`
- `infra/`: mosquitto (dev conf published on 127.0.0.1:1883, prod TLS conf, acl incl. `operator` for control topics), `caddy/Caddyfile`, `postgres/init.sql` (buoys with sensors[], measurements, incidents, alerts), `scripts/` (gen_buoy_keys.py, gen_certs.sh, server_setup.sh)
- `dashboard/`: Vite React app; `src/App.tsx` (8 routes), `src/pages/*` (placeholders, Overview calls /api/health), `src/api/client.ts`, `src/styles/theme.css`, Dockerfile (node:22-alpine + npm ci, then caddy:2; build context = repo root)
- `tests/`: conftest, test_signing, test_crypto_gate, test_physics, test_pipeline, test_api, test_clean, test_replay (incl. real Helene end-to-end without a broker)
- `seashield_concept.png`, `HackGlobal2026_Badge_B9D470.png`, `new.webp`: images

## Key concepts and decisions
- Crypto proves origin and integrity, not truth. Physics, ML, and neighbour checks cover compromised buoys (T4).
- Verdicts: TRUSTED / REJECTED / SUSPECTED_FDI / CONFIRMED_EVENT / SUPPRESSED_WARNING. Data is never deleted; a human reviews held alerts; escalate when a hidden danger is suspected.
- Verify the signature on the RAW parsed dict, never on a re-serialized model.
- `ts` = send time (replay protection); signed `observed_at` = measurement time (physics). Attack ground truth is logged outside the message.
- Engine memory reset is an OPERATOR action (`seashield/control/reset`, ACL `operator` only); it keeps replay protection. Needed when a demo jumps back in historical time.
- The network is heterogeneous; compare only shared sensors. A silent/offline neighbour = no opinion, never calm (storms knock buoys offline).
- Split: train 2023 (Idalia), validation 2024-H1, test 2024-07→2025-12 (Debby, Helene, Milton). Never tune on test.
- Engine writes the DB; the API reads the DB and streams MQTT verdicts over WebSocket (planned, Phase 7).
- One Vultr VPS (2 vCPU/4 GB, ~$20–24/mo, verify). No resource is created without user approval; a stopped instance is still billed.

## Current status
Phases 0–2 done. Live test: 233/233 messages TRUSTED (Helene + calm week after a restart with reset), 13 correct unprotected alerts in Helene, 233 verdicts back over MQTT. Physics: 0 of 94,458 real hours flagged. 41 tests pass. Real storm → TRUSTED (CONFIRMED_EVENT needs spatial, Phase 5). Docker Desktop can't start locally ("Virtual Machine Platform not enabled"; user must enable it as admin + reboot). No model, no cloud resources ($0 spent).

## Next steps
1. Phase 3: attacker CLI (tamper/replay/spike) live against the stream; ground truth in data/attack_log.jsonl
2. Phase 4: publish the baseline alert next to the SeaShield verdict

## Gotchas
- NDBC sentinels are per column (WVHT/DPD/WSPD 99, WDIR/WTMP 999, PRES 9999); 999 hPa is valid.
- pandas 3: `.to_numpy()` can be read-only (use copy=True); `interpolate(limit=n)` partially fills LONG gaps (it invented Idalia data) → use `interpolate_short_gaps`.
- NDBC 42003 and 42039 (2024+) have no files; 42022 is offline in every hurricane.
- A large multi-heredoc Bash command failed to parse in this environment; use the Write tool for files.
- Run Python through `.venv/Scripts/python` from the shell; `.env` uses Docker hostnames (set MQTT host to localhost for native runs).
- seq based on ms broke on bursts (fixed: max(prev+1, µs)); the Windows clock gives equal µs values to messages built in the same tick.
- Jumping back in replay time without `--reset` → every message is SUSPECTED_FDI ("observation time not after previous").
- Background processes for live tests: start the broker, engine and simulator as separate processes; stop them afterwards.

## Session log
- 2026-11-14: Phase 2 done: observed_at, per-hour physics limits, replay.py, simulator CLI, restart-safe seq (bug fixed), operator reset + ACL, amqtt dev broker, live E2E 233/233; PHASE_2.md.
- 2026-11-14: Phase 1 done: surveyed 11 stations, chose the West Florida cluster, clean.py + survey.py + explore.py, fixed an interpolation bug, data-notes + ADR 0003 + PHASE_1.md.
- 2026-11-14: Phase 0 done: env, keys, .env, lint fixes, test_api, npm major upgrades (0 vulns), node:22 + npm ci, .gitattributes, private repo hackathon-sea pushed; report in docs/PHASE_0.md.
- 2026-11-14: Built the full project skeleton (Python package, infra, dashboard, tests, docs) and wrote docs/PLAN.md.
- 2026-11-14: Created the master prompt and memory file.

# Project Memory: SeaShield AI

> Maintained by the project-memory skill and loaded at every session start.
> Read this first; open other files only when a task needs them.

**Last updated:** 2026-11-15 (AI layer implemented, uncommitted; waiting for the Vultr IP)
**Repo:** https://github.com/tahabenissa/hackathon-sea (private, branch main)
**Root:** D:\hackthon_sea

## What this project is
SeaShield AI is a HackGlobal 2026 hackathon project (theme: Artificial Intelligence). It is a "trust engine" that detects False Data Injection (FDI) attacks on ocean-buoy data before that data can trigger or suppress maritime alerts. It has four layers: a crypto gate (HMAC, seq, timestamp, nonce), physics checks, ML anomaly detection (Isolation Forest), and cross-buoy validation, all feeding a fusion verdict. Deployment target: Vultr, with $200 in credits (hard budget) that **expire 2026-11-16**; after that the instance bills the user's own card, so keep the plan small and destroy it once judging is over. The user wants an ambitious, high-quality project.

## Hackathon requirements (from the user, 2026-11-15)
- **Submissions close 15 November 2026** (on Vultr Community). Exact hour/timezone: ask the user.
- Tracks: Agentic/GenAI, Multimodal/accessibility, Grounded knowledge/RAG, **Civic and real-world impact** (best fit for SeaShield: a "misinformation checker" for ocean sensors that protects coastal communities).
- Deliverables: PUBLIC GitHub repo with setup + docs; backend on a Vultr Compute instance; recorded demo video running on Vultr; PUBLIC demo URL with a product-style experience; use case + system design with diagrams and screenshots of the user flow.
- Judging: Merit (idea, build, fit) · Reach (real users, shares, votes; talk to users in 3+ countries) · Bonus (cross-university teams, community challenges).

## Stack and tools
Python 3.12 (pydantic v2, pydantic-settings, paho-mqtt v2, FastAPI, SQLAlchemy 2, psycopg 3, scikit-learn, pandas 3, pyarrow, httpx; matplotlib in the `ml` extra), Mosquitto 2, PostgreSQL 16, React 18 + Vite 8.3.8 + TS (react-router removed) + Leaflet + Recharts (npm audit: 0 vulns), Caddy 2 (HTTPS + reverse proxy), Docker Compose. Dev machine: Windows 11 with Python 3.12.10, Node 24, Docker 29 and git installed. Data: NOAA NDBC stdmet.

## How to build / run / test
- `python -m venv .venv` → `.venv\Scripts\activate` → `pip install -e ".[dev,ml]"`
- `python infra/scripts/gen_buoy_keys.py` → secrets/buoy_keys.json
- Data: `python ml/download_ndbc.py <st> 2023 2024 2025` → `python ml/clean.py 42036 42097 42099 42013` → `python ml/explore.py`
- Live network without Docker: `amqtt -c infra/dev/amqtt.yaml` | `$env:SEASHIELD_MQTT_HOST="localhost"; python -m seashield.engine` | `python -m seashield.simulator --start 2024-09-25T12:00 --end 2024-09-27T12:00 --interval 1` (add `--reset` when jumping back in time)
- `pytest` → 49 passed; `ruff check .` → clean (a global ruff config also enables BLE/FURB rules)
- API: `uvicorn seashield.api.main:app --reload` (docs at /api/docs)
- Dashboard: `cd dashboard && npm install && npm run dev`
- Full stack: `cp .env.example .env` → `docker compose up -d --build` (attacker: `--profile demo`)

## File map
- `SEASHIELD_AI_MASTER_PROMPT.md`: master spec (threat model, architecture, scenarios, Vultr plan)
- `docs/PLAN.md`: opens with the **DEADLINE PLAN (15 Nov)**: deliverables status, steps D1–D10 (D1–D2 done; D3 Vultr server + D4 public repo = user), demo video script, honest limitations; then phases 0–10 as the post-hackathon roadmap, risks, checklist
- `docs/PHASE_0.md`, `PHASE_1.md`, `PHASE_2.md`, `PHASE_D6.md` (AI layer results): phase reports (what was done, results)
- `docs/data-notes.md`: **all real data facts** (cluster, coverage, outages, storms, neighbour stats, change rates, split)
- `docs/assets/phase1/`: stats.json + figures (normal week, Idalia, Helene, Milton, wave vs wind)
- `.gitattributes`: forces LF line endings (scripts and configs run on Linux)
- `tests/test_api.py`: API + WebSocket smoke tests
- `docs/architecture.md`, `docs/threat-model.md`, `docs/evaluation.md` (empty until Phase 6), `docs/decisions/0001,0002,0003` (0003 = cluster, observed_at, split)
- `pyproject.toml`, `Dockerfile` (one image for all Python services), `docker-compose.yml` (mosquitto, engine, api, simulator looping 2024-09-23→28 at 2 s/h, web=Caddy; postgres only in profile `db`), `.env.example`, `.gitignore`, `.dockerignore`
- `config/buoys.yaml`: SS-B01=42036 West Tampa (all sensors), SS-B02=42097 Pulley Ridge (waves), SS-B03=42099 St. Petersburg (waves), SS-B04=42013 C10 (wind/pressure); lat/lon + `sensors`
- `seashield/config.py`: Settings (env prefix SEASHIELD_)
- `seashield/common/`: `schema.py` (Measurements, Telemetry with `ts` + `observed_at`, Verdict, Evidence, Assessment), `signing.py` (HMAC canonical JSON), `registry.py` (Buoy has a `sensors` tuple), `mqtt.py` (`make_client`, `connect_with_retry`)
- `seashield/engine/`: `crypto_gate.py` ✅, `physics.py` ✅ (uses observed_at; per-hour limits from real data: wave 3.5 m/h, wind 15, pressure 20, temp 3; observed_at must increase and be ≤ ts+120 s; history advances only on plausible readings), `fusion.py` ✅ (risk = MAX of layer scores, not a weighted average, so one strong layer is enough for review; `AI_DECIDES=True` lets the AI score count alone, choice to be justified in docs/PHASE_D6.md), `baseline.py` ✅ (naive >6 m alert), `pipeline.py` ✅ (+ `reset_history()`), `events.py` ✅ (event JSON + SeaShield alert decision), `anomaly.py` ✅ (per-buoy Isolation Forest; `check(buoy_id, observed_at, m)` → score 0..1, flag ≥0.5, top-2 z-score features in detail; `commit()` only for accepted readings; `reset()`; no model file → score None), `features.py` ✅ (moved from ml/: `feature_names`, `feature_vector`, `training_matrix`; one implementation for train + live), `spatial.py` (stub + haversine), `__main__.py` (MQTT consumer, verdicts → `seashield/verdicts/<id>`, operator reset on `seashield/control/reset`, totals log)
- `seashield/simulator/`: `buoy.py` ✅ (VirtualBuoy; seq = max(prev+1, now µs), restart-safe), `replay.py` ✅ (shared historical clock, own sensors only, empty hour = no message), `__main__.py` ✅ (`--start --end --interval --hours --reset --loop`)
- `infra/dev/amqtt.yaml`: pure-Python dev broker on 127.0.0.1:1883 (Docker blocked locally)
- `seashield/attacker/`: `scenarios.py` ✅ (tamper, replay; compromised_spike/false_wind/suppress/drift craft FRESH signed msgs: seq+1, new nonce/ts, observed_at+30 min), `__main__.py` (stub CLI, unused: attacks run from the API)
- `seashield/api/`: `main.py` (lifespan starts the hub), `live.py` ✅ LiveHub, `ws.py` ✅ /ws/live, `routes/live.py` ✅ (/events, /stats), `routes/attacks.py` ✅, `db.py` + measurements/incidents/alerts routes (stubs)
- `ml/`: `download_ndbc.py` ✅, `clean.py` ✅ (per-column sentinels, hourly, vector wind dir, `interpolate_short_gaps`), `survey.py` ✅ (compare stations), `explore.py` ✅ (stats + figures), `train.py` ✅ (one IsolationForest+StandardScaler per buoy on real 2023, calibration q99→0, train max→0.5; writes `models/isolation_forest.joblib`, ~8.7 MB), `evaluate.py` ✅ (`--part validation|test`; replays real data through physics + AI, injects seeded +0.5..7.5 m attack twins on 2 % of hours, FP incl. storms Debby/Helene/Milton → `docs/assets/eval/<part>.json`), `README.md`
- `infra/scripts/deploy_vultr.sh`: one-command deploy (git archive + data → server, Docker, ufw 22/80/443, keys/.env on the server, sslip.io HTTPS)
- `infra/`: mosquitto (dev conf published on 127.0.0.1:1883, prod TLS conf, acl incl. `operator` for control topics), `caddy/Caddyfile`, `postgres/init.sql` (buoys with sensors[], measurements, incidents, alerts), `scripts/` (gen_buoy_keys.py, gen_certs.sh, server_setup.sh)
- `dashboard/`: single page `src/App.tsx` + `useLive.ts` + `components/` (BuoyMap Leaflet/CARTO dark, Centres, AttackConsole, WaveChart, EventFeed, HowItWorks [AI layer labelled advisory, neighbour check 'next'], VerdictBadge), `src/api/client.ts`, `src/styles/theme.css`, Dockerfile (node:22-alpine + npm ci, then caddy:2; build context = repo root)
- `tests/`: conftest, test_signing, test_crypto_gate, test_physics, test_pipeline, test_api, test_clean, test_replay (incl. real Helene end-to-end without a broker), test_live (attack console with a fake MQTT client)
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

## Deadline mode (2026-11-15)
- The 10-phase plan is cut to what the submission needs. Built: live demo (commit 1c6cf9e): engine events (`engine/events.py`: unprotected vs SeaShield alert: ISSUED/HELD/BLOCKED/REVIEW/ESCALATED), API live hub (`api/live.py`: MQTT→WS, /api/events, /api/stats, POST /api/attacks/{spike|suppress|tamper|replay}, 2 s rate limit), single-page dashboard (map, two centres, attack console, wave chart, feed, how-it-works), simulator `--loop`, compose without Postgres (profile db).
- Deploy: `bash infra/scripts/deploy_vultr.sh <IP> [domain]` (SSH key ~/.ssh/seashield_vultr, default domain <ip-dashes>.sslip.io, keys + .env generated on the server). Waiting on the user for the server IP + deadline time.
- The repo is still PRIVATE: the classifier blocked `gh repo edit --visibility public`; the user must run it.
- Honest finding: "suppress" in calm weather is undetectable (plausible); it is caught only during a storm.
- D6 done (commit 9a2bb67, docs/PHASE_D6.md): per-buoy Isolation Forest (`ml/train.py` → models/isolation_forest.joblib, git-ignored, shipped by the deploy script; features in `seashield/engine/features.py`; sklearn pinned to 1.9.1). Validation: physics 0 FP / ~75% on +4..+7.5 m fakes; AI 6 FP / 1.4%. AI deciding alone held 34/137 genuine Helene readings → `fusion.AI_DECIDES=False` (advisory, shown in explanations). Fusion now uses max evidence, not a weighted average. `ml/evaluate.py --part test` is too slow (>10 min); no test numbers claimed.

## Current status
Phases 0–2 done. Live test: 233/233 messages TRUSTED (Helene + calm week after a restart with reset), 13 correct unprotected alerts in Helene, 233 verdicts back over MQTT. Physics: 0 of 94,458 real hours flagged. 41 tests pass. Real storm → TRUSTED (CONFIRMED_EVENT needs spatial, Phase 5). Docker Desktop can't start locally ("Virtual Machine Platform not enabled"; user must enable it as admin + reboot). AI layer (Phase 5 Isolation Forest) implemented and model trained; pipeline calls `anomaly.check(..., observed_at, ...)` and commits accepted readings; evaluation results not yet recorded here (run `ml/evaluate.py`). **LIVE on Vultr since 2026-11-15:** https://45-76-249-39.sslip.io (instance `seashield-demo`, vc2-2c-4gb $20/mo, Atlanta, Ubuntu 24.04, IP 45.76.249.39, SSH key `~/.ssh/seashield_vultr` registered in Vultr as `seashield`, backups off). Deployed commit 6070d68: the AI layer is NOT on the server yet (uncommitted, and `models/*` is gitignored so the deploy script does not ship the .joblib). Redeploy = `bash infra/scripts/deploy_vultr.sh 45.76.249.39`. Destroy the instance after judging (credits expire 2026-11-16).

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
- 2026-11-15: Created the Vultr instance via Chrome, added the SSH key, deployed 6070d68: site + API health OK, engine verdicts flowing.
- 2026-11-15: AI layer: features.py moved to seashield/engine, per-buoy Isolation Forest train + calibrated scores, evaluate.py (real data + injected attacks), pipeline commit/reset wiring; fusion switched to max-risk + AI_DECIDES flag; Vultr plan advice.
- 2026-11-15: Deadline mode: live demo (engine events, API live hub + attack console, single-page dashboard), physics poison fix, deploy script; repo still private (user must flip it).
- 2026-11-14: Phase 2 done: observed_at, per-hour physics limits, replay.py, simulator CLI, restart-safe seq (bug fixed), operator reset + ACL, amqtt dev broker, live E2E 233/233; PHASE_2.md.
- 2026-11-14: Phase 1 done: surveyed 11 stations, chose the West Florida cluster, clean.py + survey.py + explore.py, fixed an interpolation bug, data-notes + ADR 0003 + PHASE_1.md.
- 2026-11-14: Phase 0 done: env, keys, .env, lint fixes, test_api, npm major upgrades (0 vulns), node:22 + npm ci, .gitattributes, private repo hackathon-sea pushed; report in docs/PHASE_0.md.
- 2026-11-14: Built the full project skeleton (Python package, infra, dashboard, tests, docs) and wrote docs/PLAN.md.
- 2026-11-14: Created the master prompt and memory file.

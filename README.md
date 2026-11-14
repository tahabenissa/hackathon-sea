# SeaShield AI

**Intelligent cybersecurity for ocean monitoring.** HackGlobal 2026 · Theme: Artificial Intelligence

SeaShield AI is a trust engine that sits between ocean buoys and a maritime early-warning
centre. It detects **False Data Injection (FDI)** attacks, both fake alarms and hidden real
dangers, by combining four layers of evidence:

1. **Crypto gate:** per-buoy HMAC signatures, sequence numbers, timestamps, nonces
2. **Physics checks:** impossible values, impossible jumps, wind/wave consistency
3. **AI anomaly detection:** Isolation Forest trained on real NOAA buoy data
4. **Cross-buoy verification:** distance-weighted comparison with neighbours

Full design: [`SEASHIELD_AI_MASTER_PROMPT.md`](SEASHIELD_AI_MASTER_PROMPT.md) ·
Architecture: [`docs/architecture.md`](docs/architecture.md) ·
Threat model: [`docs/threat-model.md`](docs/threat-model.md)

## Project layout

```
seashield/            Python package (one Docker image, several services)
  common/             message schema, HMAC signing, buoy registry, MQTT helper
  simulator/          virtual buoys replaying NOAA data as signed MQTT messages
  attacker/           SIMULATED attack scenarios (demo + evaluation)
  engine/             security engine: crypto_gate, physics, anomaly, spatial, fusion, baseline
  api/                FastAPI REST + WebSocket
ml/                   download, clean, features, train, evaluate
dashboard/            React + Vite + Leaflet + Recharts (served by Caddy)
infra/                mosquitto, caddy, postgres schema, setup scripts
config/buoys.yaml     buoy network definition
tests/                pytest suite
docs/                 architecture, threat model, decisions, evaluation
data/ models/ secrets/  git-ignored (generated locally)
```

## Quick start (local)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
python infra/scripts/gen_buoy_keys.py   # creates secrets/buoy_keys.json
pytest                                  # run the test suite
uvicorn seashield.api.main:app --reload # API docs at http://localhost:8000/api/docs
```

Dashboard (dev):

```bash
cd dashboard
npm install
npm run dev                             # http://localhost:5173
```

Full stack with Docker:

```bash
cp .env.example .env                    # then edit passwords
docker compose up -d --build
```

## Status

| Phase | Status |
|---|---|
| 0 · Design + environment + repo | ✅ done ([report](docs/PHASE_0.md)) |
| 1 · NOAA data | ✅ done: West Florida cluster, 3 years, real hurricanes ([report](docs/PHASE_1.md), [data notes](docs/data-notes.md)) |
| 2 · Simulator + MQTT | 🟡 buoy + signing done, replay source TODO |
| 3 · Crypto gate | ✅ implemented + tested |
| 4 · Unprotected baseline | ✅ implemented |
| 5 · Physics / AI / neighbours | 🟡 physics + fusion done, AI + spatial TODO |
| 6–10 · Evaluation, API+DB, dashboard, Vultr, demo | ⬜ skeletons in place |

> All attacks in this project are **simulated** on real historical data. No result here is a
> field validation.

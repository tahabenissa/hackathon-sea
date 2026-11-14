# Phase 0: Local Environment Setup (report)

**Date:** 2026-11-14
**Status:** ✅ Complete
**Repository:** https://github.com/tahabenissa/hackathon-sea (**private**, branch `main`)
**Plan reference:** [`PLAN.md` → Phase 0](PLAN.md#phase-0-local-environment-setup---1-h)

---

## 1. Goal

Make the project install and run on the development machine, make sure all existing tests
pass, and put the code under version control in a private GitHub repository, **without
leaking any secret**.

---

## 2. Development environment (measured)

| Tool | Version |
|---|---|
| OS | Windows 11 Home |
| Python | 3.12.10 |
| pytest | 9.2.0 |
| Node.js | 24.18.0 |
| npm | 12.0.2 |
| Docker | 29.6.2 |
| git | 2.55.0 |
| GitHub CLI (`gh`) | 2.97.0 |

---

## 3. What was done, step by step

### Step 1: Python virtual environment
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
```
- Installs the `seashield` package in **editable** mode (code changes apply immediately)
  plus dev tools (`pytest`, `ruff`).
- Result: `Successfully installed seashield-0.1.0`.
- The setuptools message *"be careful with folders with the same name as your package"* is
  expected and harmless: the `seashield/` folder **is** the package.

### Step 2: Per-buoy secret keys
```powershell
.venv\Scripts\python infra/scripts/gen_buoy_keys.py
```
- Result: `Wrote 4 keys to secrets/buoy_keys.json`: one random 256-bit HMAC key for each of
  SS-B01, SS-B02, SS-B03, SS-B04.
- The file is **git-ignored** and was verified absent from the GitHub repo (step 9).

### Step 3: Environment file
- `.env` created from `.env.example`, with `change-me` replaced by a **random 32-character
  password** (generated with Python `secrets.token_urlsafe(24)`) in both `POSTGRES_PASSWORD`
  and `SEASHIELD_DATABASE_URL`.
- `.env` is git-ignored. Note: it uses Docker service names (`mosquitto`, `postgres`); for
  running services directly on Windows in Phase 2, set `SEASHIELD_MQTT_HOST=localhost`.

### Step 4: Test suite (first run)
```powershell
.venv\Scripts\python -m pytest -v
```
- Result: **19 passed** (signing ×4, crypto gate ×6, physics ×6, pipeline ×3).
- This confirms on real code that:
  - tampered messages are rejected (signature check)
  - replays are rejected (sequence number and nonce)
  - messages with an old timestamp are rejected
  - a **compromised buoy passes crypto** (expected) but is then caught as `SUSPECTED_FDI`
    by the physics layer, while the **unprotected baseline fires a fake alert**

### Step 5: Lint (ruff) and two fixes
```powershell
.venv\Scripts\python -m ruff check .
```
Two findings, both fixed:

| File | Finding | Fix |
|---|---|---|
| `seashield/engine/crypto_gate.py` | `FURB162`: unnecessary `.replace("Z", "+00:00")` | Removed; Python ≥ 3.11 `fromisoformat` accepts `Z` |
| `seashield/api/ws.py` | `BLE001`: catching a bare `Exception` | Now catches only `WebSocketDisconnect, RuntimeError` |

Result after fixes: `All checks passed!`

### Step 6: API smoke test → new permanent tests
- Called the API in-process with FastAPI's `TestClient`:

| Endpoint | Result |
|---|---|
| `GET /api/health` | 200 `{"status":"ok","version":"0.1.0"}` |
| `GET /api/buoys` | 200, the 4 configured buoys |
| `GET /api/attacks/scenarios` | 200, 6 scenarios |
| `GET /api/docs` | 200, Swagger UI |
| `WS /ws/live` | connection accepted |

- These checks were saved as **`tests/test_api.py`** (4 tests) so they run every time.

### Step 7: Dashboard install, security audit, build
```powershell
cd dashboard
npm install
npm audit
npm run build
```
- The first `npm audit` reported **5 vulnerabilities (1 moderate, 4 high)** in
  `react-router` and `vite`/`esbuild`.
- First attempt: patch upgrades (`react-router-dom 6.30.6`, `vite 5.4.21`) left
  **5 (4 moderate, 1 high)**. The remaining fixes only exist in newer major versions.
- Analysis: every remaining issue affected the **development server** or features we do not
  use (SSR). In production, Caddy serves pre-built static files. Since the pages are still
  placeholders, upgrading now costs almost nothing, so we upgraded:

| Package | Before | After |
|---|---|---|
| `vite` | 5.4.8 | **8.3.8** |
| `@vitejs/plugin-react` | 4.3.1 | **6.3.0** |
| `react-router-dom` | 6.26.2 | **7.18.5** |

- Result: **`found 0 vulnerabilities`**. Versions pinned exactly; `package-lock.json` committed.
- `npm run build` (TypeScript type-check + Vite production build) → success,
  `index.js` 182 kB (60 kB gzip). No code change was needed for React Router 7.

### Step 8: Docker image fixes (found while upgrading)
`dashboard/Dockerfile`:
- `node:20-alpine` → **`node:22-alpine`**: Vite 8 needs a recent Node, and Node 20 is past end of life.
- `npm install` → **`npm ci`**: reproducible builds from the committed lockfile.

### Step 9: Git repository + private GitHub repo
1. Added **`.gitattributes`** forcing **LF line endings**. Without it, git on Windows
   would convert files to CRLF, which **breaks shell scripts and Mosquitto configs on the
   Linux server**. Verified: 0 files with CRLF in the repository.
2. `git init -b main`, staged everything, then **checked that no secret was staged**
   (`.env`, `secrets/buoy_keys.json`, `node_modules`, `.venv`, `dist` all absent).
3. Initial commit `eafa468`: *"SeaShield AI: project skeleton (Phase 0)"*.
4. Re-ran the full suite before pushing: **23 passed**, ruff clean.
5. Created the GitHub repository and pushed:
   ```powershell
   gh repo create hackathon-sea --private --source=. --remote=origin --push
   ```
6. Verified on GitHub: visibility **PRIVATE**, default branch `main`, 129 tracked paths,
   remote `secrets/` folder contains **only `.gitkeep`**.

---

## 4. Final results

| Check | Result |
|---|---|
| Python package installs | ✅ |
| Buoy keys generated (local only) | ✅ 4 keys |
| `.env` with random DB password (local only) | ✅ |
| Tests | ✅ **23 passed** (1 deprecation warning from the FastAPI test client, harmless) |
| Lint (ruff) | ✅ All checks passed |
| API endpoints + WebSocket | ✅ |
| Dashboard type-check + production build | ✅ |
| npm audit | ✅ 0 vulnerabilities |
| Git repo, LF line endings, no secrets committed | ✅ |
| Private GitHub repo `hackathon-sea` | ✅ https://github.com/tahabenissa/hackathon-sea |
| Cloud resources created / money spent | **none / $0** |

---

## 5. Differences from the plan

- The API was verified with `TestClient` (in-process) and the dashboard with a full
  production build, instead of opening them manually in a browser. To see them yourself:
  - `.venv\Scripts\activate` → `uvicorn seashield.api.main:app --reload` →
    http://localhost:8000/api/docs
  - `cd dashboard` → `npm run dev` → http://localhost:5173 (Overview card should show "ok"
    while the API runs)
- The Docker stack was **not** started. It is not needed until Phase 2 (Mosquitto) and
  Phase 7 (Postgres).
- Extra work not in the plan: `tests/test_api.py`, dependency security upgrades,
  `.gitattributes`, Dockerfile fixes.

---

## 6. How to set up on another machine (teammate or Vultr server)

```powershell
git clone https://github.com/tahabenissa/hackathon-sea.git
cd hackathon-sea
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
python infra/scripts/gen_buoy_keys.py  # or copy secrets/ securely (scp), NEVER via git
copy .env.example .env                 # Linux: cp; then set a strong password
pytest
cd dashboard; npm ci; npm run build
```

Secrets (`.env`, `secrets/buoy_keys.json`) are **never** in the repository. Each machine
generates its own, or receives them through a secure channel.

---

## 7. Next: Phase 1 (real ocean data)

1. Choose a cluster of 3–5 nearby NOAA NDBC buoys with a documented storm.
2. Fill `config/buoys.yaml` (station, lat, lon).
3. Download history with `ml/download_ndbc.py`, implement `ml/clean.py`.
4. Explore the data and write real observations in `docs/data-notes.md`.

# SeaShield AI: Detailed Implementation Plan

> Step-by-step plan from the current skeleton to a cloud-deployed, demo-ready prototype.
> Companion documents: [`../SEASHIELD_AI_MASTER_PROMPT.md`](../SEASHIELD_AI_MASTER_PROMPT.md) (the *what* and *why*),
> [`architecture.md`](architecture.md), [`threat-model.md`](threat-model.md).

---

## 0. How to read this plan

Every phase has the same structure:

- **Goal:** what we get at the end
- **Steps:** what to do, in order, with the files involved
- **Done when:** a test you can run or show; if it doesn't pass, the phase isn't finished
- **Pitfalls:** traps to avoid

**Golden rules for the whole project**
1. One phase at a time. Every phase ends with something that **works and can be shown**.
2. Commit to git at the end of every step that works.
3. Never invent numbers (metrics, dataset stats, prices). Measure them.
4. Never create a paid cloud resource without checking the cost first.
5. Demo-critical features before nice-to-have features (see the [priority list](#13-if-time-runs-short-priority-cut-list)).

**Effort estimates** are for one developer working focused hours. Adjust to the hackathon deadline.

---

## 1. Where we are now

| Area | State |
|---|---|
| Design (master prompt, threat model, architecture, ADRs) | ✅ Done |
| Folder structure + config files + Docker Compose | ✅ Done |
| Message schema, HMAC signing, buoy registry | ✅ Written |
| Crypto gate (signature, seq, timestamp, nonce) | ✅ Written |
| Physics checks, fusion rules, unprotected baseline | ✅ Written (thresholds are initial heuristics) |
| Attack scenarios (tamper, replay, spike, wind, suppress, drift) | ✅ Written as functions |
| Tests (signing, crypto gate, physics, pipeline, API) | ✅ **23 passing** (Phase 0, see [`PHASE_0.md`](PHASE_0.md)) |
| Environment, git, private repo `hackathon-sea` | ✅ Phase 0 done |
| NOAA data, simulator replay, ML model, spatial check | ⬜ Skeleton only |
| API persistence, WebSocket feed, dashboard pages | ⬜ Skeleton only |
| Vultr deployment | ⬜ Not started (no resource created, $0 spent) |

---

## Phase 0: Local environment setup  ·  ~1 h

**Goal:** the project installs and the existing tests pass on your machine.

**Steps**
1. Open a terminal in `D:\hackthon_sea`.
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install the package and dev tools: `pip install -e ".[dev]"`
4. Generate the per-buoy secret keys: `python infra/scripts/gen_buoy_keys.py`
   → creates `secrets/buoy_keys.json` (git-ignored, never share it).
5. Copy the environment file: `copy .env.example .env`, then change `POSTGRES_PASSWORD`
   (and the same password inside `SEASHIELD_DATABASE_URL`).
6. Run the tests: `pytest -v`
7. Fix anything that fails *before* moving on.
8. Initialise git and make the first commit:
   ```powershell
   git init
   git add .
   git commit -m "SeaShield AI: project skeleton"
   ```
   Check with `git status` that `secrets/buoy_keys.json` and `.env` are **not** committed.
9. Create a **private** GitHub repository and push (needed later to deploy on Vultr).
10. Dashboard dependencies: `cd dashboard`, `npm install`, `npm run dev` → open http://localhost:5173.

**Done when**
- `pytest` → all green.
- `uvicorn seashield.api.main:app --reload` → http://localhost:8000/api/docs opens and `/api/health` returns `ok`.
- Dashboard opens and the Overview card shows "ok".

**Pitfalls**
- PowerShell may block `activate`: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- If you ever commit a key by mistake: regenerate the keys (`--force`). Deleting the file from git is not enough, because the key stays in the history.

---

## Phase 1: Real ocean data (NOAA NDBC)  ·  ~4–6 h

**Goal:** clean, real buoy data from a **cluster of nearby buoys**, including **at least one real storm**.

**Steps**
1. **Choose the buoy cluster** on https://www.ndbc.noaa.gov/ (station map). Criteria:
   - 3–5 moored buoys, roughly **30–300 km apart** (close enough to see the same weather).
   - They report **WVHT** (wave height), **WSPD** (wind), **PRES** (pressure), **DPD** (period), **WTMP**.
   - Several years of history available for the same years.
   - The area had **documented storms** (hurricane season, winter nor'easters…). Pick 1–2 named
     storms with known dates. They are our "real extreme event" test cases.
2. Write the chosen station IDs and positions into `config/buoys.yaml`
   (`ndbc_station`, `lat`, `lon` for SS-B01…SS-B04).
3. **Download** 2–3 years per station:
   `python ml/download_ndbc.py <station> 2023 2024 2025`
   → `data/raw/<station>h<year>.txt.gz`. If a URL fails, check the station's history page and
   adjust `URL` in `ml/download_ndbc.py`.
4. **Implement `ml/clean.py`** (the TODO steps in the file):
   - read with `pd.read_csv(sep=r"\s+", skiprows=[1])` (line 2 is units)
   - build a UTC timestamp from `#YY MM DD hh mm`
   - replace `99 / 999 / 9999` with NaN **per column**
   - rename columns to the SeaShield names (`COLUMNS` mapping)
   - resample to a fixed step (1 h is the safest for NDBC history; 10 min if available)
   - interpolate only short gaps (≤ 2 steps), leave long gaps as NaN
   - save `data/processed/<station>.parquet`, print a data-quality report (rows, % missing per column, date range)
   - add `pyarrow` to `pyproject.toml` dependencies (needed for parquet)
5. **Explore the data** in a notebook `ml/notebooks/01_explore.ipynb`:
   - plot wave height / wind / pressure for each buoy over a normal month
   - plot the **storm window**: do neighbours rise together? With what delay?
   - scatter wave height vs wind speed (this validates the physics thresholds)
   - correlation of wave height between buoy pairs vs distance
6. Write down **real** observations (not guesses) in `docs/data-notes.md`: date ranges,
   missing %, storm dates, max wave height seen, typical neighbour difference.
7. **Define the time split** now and write it in `docs/data-notes.md`:
   - *train*: earlier period, normal data (e.g. first 70 % of the timeline)
   - *test*: later period, must contain at least one real storm
8. Commit.

**Done when**
- `data/processed/*.parquet` exists for every buoy.
- The notebook shows a normal period and a real storm across several buoys.
- `docs/data-notes.md` lists the storm windows and the train/test split.

**Pitfalls**
- NDBC uses `99.00`, `999`, `9999.0` for "missing". If you forget this, the model learns that
  99 m waves are normal.
- Some old files have a different header format (no minute column). Check the first lines of each file.
- Note the NOAA source and citation for the README (public-domain US government data; still cite it).

---

## Phase 2: Buoy simulator over MQTT  ·  ~3–4 h

**Goal:** virtual buoys replay the real data as signed messages through Mosquitto, and the engine receives them.

**Steps**
1. **Implement `seashield/simulator/replay.py`**: read the parquet, optional `start` date,
   yield `Measurements` per row (NaN → `None`).
2. **Time compression:** one historical hour = one message every `SEASHIELD_PUBLISH_INTERVAL_S`
   seconds (2 s default). A 3-day storm then replays in ~2.5 min, which is perfect for a live demo.
3. Add a **scenario start option** to the simulator (`--start 2024-09-10T00:00`) so the demo can
   jump straight to a calm period or to the storm.
4. **Sequence numbers across restarts:** `VirtualBuoy` currently starts `seq` at 0, so a
   restarted simulator would be rejected as a replay. Fix: start `seq` from
   `int(time.time() * 1000)` (monotonic enough), or persist the last value. Add a test.
5. Start the broker only: `docker compose up -d mosquitto`, and expose it to your machine
   for development by temporarily adding `ports: ["127.0.0.1:1883:1883"]` (local only).
6. Run the engine and the simulator in two terminals:
   `python -m seashield.engine` / `python -m seashield.simulator`
   with `SEASHIELD_MQTT_HOST=localhost` in `.env` for local runs.
7. Watch the engine logs: every message should show `verdict=TRUSTED`.
8. Use a GUI client (MQTT Explorer) to inspect topics `seashield/buoys/#` and `seashield/verdicts/#`.
9. Commit.

**Done when**
- 4 buoys publish continuously; the engine logs one `TRUSTED` verdict per message.
- Replaying the storm window: the **unprotected** baseline logs `HIGH_WAVES` alerts, and the
  engine does not reject the real storm (it may still say SUSPECTED until Phase 5 adds neighbours).

**Pitfalls**
- The `ts` field must be the **send time** (now), not the historical time. Otherwise the replay
  window rejects everything. The historical time can be added later as `observed_at` if needed.
- paho-mqtt v2 needs `CallbackAPIVersion.VERSION2` (already handled in `common/mqtt.py`).

---

## Phase 3: Crypto gate live + attacker tool  ·  ~3 h

**Goal:** attacks T1 (tampering), T2 (fake device) and T3 (replay) are launched live and rejected.

**Steps**
1. **Implement `seashield/attacker/__main__.py`** (CLI mode):
   - subscribe to `seashield/buoys/<target>/telemetry`, capture the next real message
   - apply the scenario from `attacker/scenarios.py`
   - publish the forged message on the same topic
   - write the ground truth (`time, buoy, seq, scenario`) to `data/attack_log.jsonl`,
     never inside the message
2. Scenarios to wire now: `tamper`, `replay`, `spike` (needs the buoy key: this simulates a
   **compromised** buoy, so the attacker reads it from `secrets/`).
3. Run: `python -m seashield.attacker --scenario tamper --buoy SS-B01`
4. Check the engine logs:
   - tamper → `REJECTED: signature invalid`
   - replay → `REJECTED: sequence … replay` or `nonce already used`
   - spike → passes crypto (expected!) → `SUSPECTED_FDI` from the physics jump rule
5. Add an integration test that runs the pipeline on a recorded sequence of messages
   (normal → tamper → replay → spike) and checks each verdict.
6. Commit.

**Done when** all three attacks give the expected verdict live, and the unprotected baseline
fires a fake `HIGH_WAVES` alert for the spike.

**Pitfalls**
- Do not let the engine read `attack_log.jsonl`. Ground truth is only for evaluation (Phase 6).

---

## Phase 4: Unprotected baseline as a real "second centre"  ·  ~1–2 h

**Goal:** a clear "without SeaShield" story, recorded alongside the SeaShield results.

**Steps**
1. `engine/baseline.py` already fires `HIGH_WAVES` above 6 m. Keep it deliberately naive.
2. In the engine, for every message record **both** decisions:
   `unprotected_alert` (issued or not) and SeaShield verdict (+ alert state ISSUED / HELD).
3. Publish both on MQTT (`seashield/verdicts/<id>` includes a `baseline_alert` field) so the
   dashboard can show them side by side later.
4. Commit.

**Done when** for the spike attack, logs show *unprotected: ALERT ISSUED* and *SeaShield: HELD*.

---

## Phase 5: Detection layers (physics, AI, neighbours, fusion)  ·  ~8–12 h

This is the heart of the project. Do it in this order.

### 5.1 Calibrate physics thresholds  ·  ~1–2 h
1. Using the Phase 1 notebook, measure on **real data** (training period):
   - the 99.9th percentile of hourly change for wave height, wind, pressure, temperature
   - the relation between wave height and wind speed (including swell cases with long period)
2. Update `MAX_RATE_PER_MIN`, `BIG_WAVES_M`, `CALM_WIND_MS`, `SWELL_PERIOD_S` in
   `engine/physics.py` from these measurements, with a comment citing the notebook.
3. Run the physics checker over the **whole real storm**: it must produce **zero or near-zero**
   violations. If it flags the real storm, loosen the rule. Write down the choice in
   `docs/decisions/0003-physics-thresholds.md`.

### 5.2 Feature engineering  ·  ~2 h
1. Implement `ml/features.py → build_features(df)` with the features listed in `FEATURES`
   (raw values, deltas, rolling mean/std over 6 steps, wave/wind ratio, hour and day-of-year as sin/cos).
2. Make the **live engine use the same function**: keep a small rolling buffer per buoy
   in `engine/anomaly.py` and call `build_features` on it. Same code offline and live.
3. Unit test: features of a known tiny DataFrame give the expected values.

### 5.3 Train the Isolation Forest  ·  ~2 h
1. Implement `ml/train.py`: load training period, `build_features`, drop NaN rows,
   `StandardScaler` + `IsolationForest(n_estimators=200, contamination="auto", random_state=42)`.
2. Save with joblib to `models/isolation_forest.joblib` together with metadata
   (feature list, training dates, sklearn version).
3. Option A (simple): one model for all buoys. Option B (better): one model per buoy.
   Start with A; switch to B only if evaluation shows it helps.
4. Implement `engine/anomaly.py → check()`: load the model, compute score, map to 0–1
   (calibrate with percentiles of training scores: e.g. 99th percentile → 0.5), and put the
   **top 3 contributing features** in `detail` (largest standardized deviations is a fine first version).

### 5.4 Cross-buoy (spatial) verification  ·  ~3 h
1. Implement `engine/spatial.py → check()`:
   - neighbours = other buoys with a **trusted** reading in the last N minutes and known position
   - expected value = inverse-distance-weighted mean of neighbours' values
   - tolerance = base + k × distance (calibrate `base` and `k` from the real neighbour
     differences measured in Phase 1)
   - score = how many tolerances the reading is away (clipped to 0–1)
2. Also compute **`neighbours_see_storm`**: True if most neighbours report wave height above the
   storm threshold or a strong pressure drop. Return it alongside the evidence (e.g. extend the
   return value or store it on the checker) and pass it to `fuse()` in `engine/pipeline.py`.
3. Tests: lone spike → high score; all buoys rising together → low score and `neighbours_see_storm=True`.

### 5.5 Fusion tuning  ·  ~1–2 h
1. Check `engine/fusion.py` against the decision table of the master prompt:
   normal → TRUSTED · real storm → CONFIRMED_EVENT · compromised spike → SUSPECTED_FDI ·
   calm-during-storm → SUPPRESSED_WARNING · tamper/replay → REJECTED.
2. Write one test per row of that table (`tests/test_fusion.py`).
3. Tune `WEIGHTS` and `SUSPICIOUS_RISK` only on the **training/validation** period, never on the test set.

### 5.6 Stretch: slow drift (T5)  ·  ~2 h
Add a per-buoy CUSUM on the residual "reading − neighbour estimate". It raises evidence when a
small bias accumulates over time. Only if everything above already works.

**Done when (whole Phase 5)**
- Real storm replay → **CONFIRMED_EVENT**, alert goes out.
- Compromised spike / false wind → **SUSPECTED_FDI**, alert held.
- Suppression during storm → **SUPPRESSED_WARNING**.
- Tamper / replay → **REJECTED**.
- All tests green.

---

## Phase 6: Evaluation (real numbers)  ·  ~4–6 h

**Goal:** honest, reproducible metrics that prove each layer earns its place.

**Steps**
1. Implement `ml/evaluate.py` running **offline** (no MQTT) on the **test period**:
   1. Replay the test data through `SecurityPipeline` buoy by buoy, in time order.
   2. Inject attacks at random but **seeded** positions (`random_state=42`), labelled:
      - spike FDI at magnitudes +10 %, +25 %, +50 %, +100 %, +200 %, +500 %
      - false wind, suppression (inside the storm window only), replay, tamper, drift
   3. Keep the clean storm window **uninjected** to measure false positives on real extremes.
2. Compute and save:
   - precision, recall, F1, false-positive rate (overall and **during real storms**)
   - **detection rate vs attack magnitude** curve (plot)
   - detection latency (messages until first flag, for drift)
   - average processing time per message (ms) and peak memory
   - **ablation table**: crypto only → +physics → +AI → +spatial
   - **unprotected vs SeaShield**: fake alerts issued, real alerts missed, real alerts issued
3. Write results to `docs/evaluation.md` and plots to `docs/assets/` **automatically**
   from the script (no hand-typed numbers).
4. Interpret honestly: where does it fail? (Small attacks, coordinated attacks.) Put that in
   a "Limitations" section. Judges trust projects that know their limits.
5. Commit, including the exact command and seed used.

**Done when** `python ml/evaluate.py` regenerates `docs/evaluation.md` end to end.

**Pitfalls**
- Never shuffle time series before splitting (data leakage).
- Never tune thresholds on the test set.
- State clearly: *"simulated attacks on real historical NOAA data"*.

---

## Phase 7: API + database + live feed  ·  ~5–6 h

**Goal:** everything is persisted and streamed to the browser in real time.

**Decision:** the **engine writes to PostgreSQL** directly; the **API reads** PostgreSQL for
history and **subscribes to `seashield/verdicts/#`** to push live updates over WebSocket.

**Steps**
1. Start Postgres: `docker compose up -d postgres` (schema auto-created from `infra/postgres/init.sql`).
2. Create SQLAlchemy models in `seashield/api/models.py` matching `init.sql`
   (`buoys`, `measurements`, `incidents`, `alerts`).
3. Seed the `buoys` table from `config/buoys.yaml` at engine startup (upsert).
4. Engine: after each assessment, insert a `measurement`; if verdict ≠ TRUSTED insert an
   `incident` with evidence JSON; insert `alerts` rows for **both** pipelines.
5. API endpoints (files already exist in `seashield/api/routes/`):
   - `GET /api/buoys`: registry + latest verdict per buoy
   - `GET /api/measurements?buoy_id=&limit=`: history for charts
   - `GET /api/incidents?status=`: incident list with evidence
   - `POST /api/incidents/{id}/review`: operator decision → releases or discards the held alert
   - `GET /api/alerts?pipeline=`: for the side-by-side view
   - `GET /api/health`: + DB ping, MQTT connected, messages/min
6. WebSocket `/ws/live`: start a background MQTT subscriber on app startup (FastAPI lifespan),
   forward every verdict to `broadcast()` in `seashield/api/ws.py`.
7. **Protect write endpoints** (`/attacks/*`, `/incidents/*/review`) with a simple demo token
   from `.env` (`SEASHIELD_DEMO_TOKEN`), so strangers on the public URL cannot trigger attacks.
8. Tests with FastAPI `TestClient` for each endpoint.
9. Commit.

**Done when** `docker compose up` runs the whole backend, history survives a restart, and a
WebSocket client receives verdicts live.

---

## Phase 8: Dashboard  ·  ~10–14 h

**Goal:** a judge understands the project in 30 seconds without reading anything.

Build pages in **demo-priority order**:

| Order | Page | Content | File |
|---|---|---|---|
| 1 | **Unprotected vs SeaShield** | Two panels on the same stream: left fires a fake alert, right holds it with evidence | `pages/Comparison.tsx` |
| 2 | **Buoy map** | Leaflet map, real positions, marker colour = verdict, popup with latest reading | `pages/BuoyMap.tsx` |
| 3 | **Attack console** | Buttons per scenario + target buoy, big "SIMULATION" label, demo token | `pages/AttackConsole.tsx` |
| 4 | **Live ocean data** | Recharts lines per buoy; flagged points red, held points amber | `pages/LiveData.tsx` |
| 5 | **Incidents & alerts** | Timeline, explanation sentence, per-layer evidence, approve/reject buttons | `pages/Incidents.tsx` |
| 6 | **AI detection** | Anomaly score over time, top contributing features | `pages/AiDetection.tsx` |
| 7 | **Overview** | KPIs: trusted buoys, open incidents, alerts held vs issued | `pages/Overview.tsx` |
| 8 | **System health** | Message rate, latency, CPU/RAM, service status | `pages/SystemHealth.tsx` |

**Steps**
1. Create a shared live store (React context) fed by `connectLive()` in `src/api/client.ts`;
   every page reads from it, so there is only one WebSocket.
2. Build pages in the order above; after each page, test it with the simulator + attacker running.
3. Every flagged item shows the **explanation sentence** from the engine
   (e.g. *"Signature valid. 9.0 m waves with 6 m/s wind. Neighbours report 1.7–1.8 m. Alert held."*).
4. Visual polish: theme in `src/styles/theme.css` (navy, cyan, green / amber / red / violet),
   subtle animation when a verdict changes, mobile layout check at phone width.
5. Add a small "About / How it works" panel with the 4-layer diagram for non-experts.
6. Commit after each page.

**Done when** someone who has never seen the project can watch a 1-minute attack and explain
back what happened.

**Pitfalls**
- Don't build all 8 pages half-way. Finish pages 1–3 completely first.
- Leaflet needs its CSS (`import "leaflet/dist/leaflet.css"`) or the map renders broken.

---

## Phase 9: Vultr deployment  ·  ~4–6 h  ·  💰 the only phase that spends credit

**Goal:** the full stack runs on a public HTTPS URL, within budget.

### 9.1 Before spending anything
1. Log in to Vultr → **Billing**: confirm the $200 credit is applied and note the expiry date.
2. Check the **current** price of a Cloud Compute instance with 2 vCPU / 4 GB
   (expected ~$20–24/month, billed hourly, verify on the page).
3. Decide and write down in the table at the end of this file: plan, region, expected monthly cost.
4. ✋ **Confirm before clicking "Deploy".**

### 9.2 SSH key (on your Windows machine)
1. `ssh-keygen -t ed25519 -C "seashield-vultr"` → keep the default path, set a passphrase.
2. Vultr → **Account → SSH Keys → Add**: paste the content of `~/.ssh/id_ed25519.pub`.

### 9.3 Create the server
1. **Deploy New Server → Cloud Compute (shared CPU)**.
2. **Location:** the region closest to you and the judges.
3. **Image:** Ubuntu 24.04 LTS x64.
4. **Plan:** 2 vCPU / 4 GB.
5. **Additional features:** leave **automatic backups OFF** (extra cost); IPv6 optional (free).
6. **SSH key:** select the one you added. **Hostname:** `seashield`.
7. Deploy, note the **public IP**.

### 9.4 Firewall (free)
1. Vultr → **Network → Firewall → Add Firewall Group** `seashield-fw`:
   - TCP 22 from **your IP only**
   - TCP 80, 443 from anywhere
   - TCP 8883 from anywhere (MQTT over TLS, only if remote buoys are needed)
2. Attach the group to the instance.
3. **Never** open 1883 (plain MQTT), 5432 (Postgres) or 8000 (API) publicly.

### 9.5 Harden the server
1. `ssh root@<IP>`
2. Copy `infra/scripts/server_setup.sh` to the server, **read it**, then run
   `bash server_setup.sh <your-username>`. It creates a sudo user, disables password and root
   login, enables `ufw` + `fail2ban` + automatic security updates, and installs Docker.
3. Open a **second** terminal and check `ssh <user>@<IP>` works **before** closing the root session.

### 9.6 Domain + HTTPS
1. Get a domain: a free DuckDNS subdomain or a cheap domain.
2. Create an **A record** → the server IP. Wait until `nslookup <domain>` returns the IP.
3. Set `SEASHIELD_DOMAIN=<domain>` in the server's `.env`. Caddy gets the Let's Encrypt
   certificate automatically on first start.

### 9.7 Deploy the stack
1. On the server: `git clone` your private repo (use a GitHub deploy key or a fine-grained token).
2. Create `.env` on the server (strong passwords; **not** copied through git).
3. Generate buoy keys **on the server**: `python3 infra/scripts/gen_buoy_keys.py`
   (or copy `secrets/` with `scp`, never through git).
4. Copy the trained model `models/isolation_forest.joblib` with `scp` (models are git-ignored).
5. Copy the processed data `data/processed/*.parquet` with `scp` (the simulator needs it).
6. `docker compose up -d --build`, then `docker compose ps` and `docker compose logs -f engine`.
7. Production MQTT: `bash infra/scripts/gen_certs.sh <domain>`, create users with
   `mosquitto_passwd`, switch the mosquitto volume to `mosquitto.prod.conf` + `passwd` + `acl` +
   `certs`, publish port 8883. (Optional for the demo if all buoys run on the server.)

### 9.8 Verify
- `https://<domain>` loads the dashboard from your **phone on mobile data**.
- `https://<domain>/api/health` → ok.
- Launch an attack from the console → verdict appears live.
- Run an SSL check on the domain: the certificate is valid.

### 9.9 Operate and control cost
- Check **Vultr → Billing** every day; fill the budget table below.
- Watch CPU / RAM / disk / bandwidth graphs in the Vultr instance page; `docker stats` on the server.
- `docker system prune` occasionally (disk).
- ⚠️ A **stopped** instance is **still billed**. Only **Destroy** stops billing.
- Optional: one **snapshot** right before the demo (small cost per GB/month), deleted after.
- After the hackathon: export what you need, then **destroy** the instance, snapshots, and reserved IPs.

**Done when** the public URL works end to end and spending matches the estimate.

---

## Phase 10: Demo, pitch and submission  ·  ~6–8 h

**Steps**
1. **Demo mode** (one click/command) that resets the database and starts the simulator on a
   calm period, so every rehearsal starts identically.
2. Follow the **4-minute demo script** (master prompt §12):
   calm network → attack → unprotected fake alarm vs SeaShield held → tamper/replay rejected →
   real storm **confirmed** → hidden storm flagged → results table → public URL.
3. Record a **backup video** of the full demo (in case Wi-Fi fails on the day).
4. Slides (≈8): problem · why it matters · threat model · 4-layer solution · architecture ·
   live demo · results (from `docs/evaluation.md`) · impact and future work.
5. Update `README.md`: screenshots, public URL, how to run, data citation, limitations.
6. Rehearse **3 times** with a timer. Prepare answers for likely judge questions:
   - *"What if the attacker steals the key?"* → T4, physics + AI + neighbours.
   - *"How do you not block real storms?"* → CONFIRMED_EVENT, storm test result.
   - *"What about coordinated attacks?"* → honest limitation + mitigation idea.
   - *"Is the AI just flagging outliers?"* → evidence vs proof, fusion, ablation table.
7. Submit: repo link, demo URL, video, description (problem / idea / who it helps / impact).

**Done when** the demo runs 3 times in a row without surprises, under 5 minutes.

---

## 11. Cross-cutting practices (every phase)

| Topic | Practice |
|---|---|
| Git | Small commits with clear messages; never commit `.env`, `secrets/`, `data/`, `models/` |
| Tests | Every new rule or layer gets a test; `pytest` green before each commit |
| Docs | Each significant choice → a short ADR in `docs/decisions/` |
| Security | Secrets only in `.env` / `secrets/`; demo token on write endpoints; firewall minimal |
| Honesty | Label simulated attacks; numbers only from `ml/evaluate.py` |
| Memory | Update `PROJECT_MEMORY.md` at the end of each session |

---

## 12. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| NDBC stations lack a field (e.g. no PRES) | Physics/spatial weaker | Choose stations in Phase 1 by checking columns first |
| Physics/AI flag the real storm | Main claim fails | Calibrate on the real storm (5.1), test CONFIRMED_EVENT explicitly |
| Simulator restart → replay rejections | Demo breaks | Time-based seq start (Phase 2 step 4) |
| Running out of time | Unfinished demo | Follow the priority cut list below |
| Wi-Fi fails during demo | No live demo | Backup video + local Docker stack on laptop |
| Credit consumed by mistake | Budget lost | One instance only, daily billing check, destroy after |
| Key leaked to GitHub | Security story undermined | `.gitignore`, check `git status`, rotate keys if leaked |

---

## 13. If time runs short: priority cut list

**Must have (the demo fails without it)**
1. Real NOAA data replayed by signed virtual buoys
2. Crypto gate: tamper + replay rejected
3. Compromised spike: unprotected fake alarm vs SeaShield held
4. Real storm **not** flagged as an attack
5. Comparison page + map + attack console
6. Public HTTPS URL on Vultr

**Should have**
7. Isolation Forest layer with explanations
8. Spatial layer + suppressed-warning detection
9. Evaluation with ablation table
10. Incidents page with operator review

**Nice to have**
11. Drift detection (CUSUM), Ed25519 signatures, MQTT TLS for remote buoys
12. Autoencoder model, per-buoy models
13. System health page with live resource graphs

---

## 14. Budget tracker (fill in as you go)

| Date | Resource | Plan / size | Price (verified) | Running total | Credit left |
|---|---|---|---|---|---|
| — | none yet | — | — | $0 | $200 |

---

## 15. Master checklist

- [x] Phase 0: environment works, tests green, first commit, private repo → [`PHASE_0.md`](PHASE_0.md)
- [ ] Phase 1: buoy cluster chosen, data cleaned, storm identified, split defined
- [ ] Phase 2: simulator replays data over MQTT, engine receives
- [ ] Phase 3: attacker CLI; tamper/replay rejected; spike held
- [ ] Phase 4: unprotected vs SeaShield recorded side by side
- [ ] Phase 5: physics calibrated, AI trained, spatial done, fusion tested
- [ ] Phase 6: `evaluate.py` produces real metrics + ablation
- [ ] Phase 7: API + DB + WebSocket + demo token
- [ ] Phase 8: dashboard pages 1–3 complete, then 4–8
- [ ] Phase 9: Vultr instance, firewall, HTTPS, stack running, budget tracked
- [ ] Phase 10: demo mode, backup video, slides, README, 3 rehearsals, submitted

# SeaShield AI — Master Project Prompt

> **Intelligent cybersecurity for ocean monitoring.**
> Detecting False Data Injection (FDI) attacks on maritime early-warning systems with machine learning, cryptography, physics, and cross-buoy validation.

| | |
|---|---|
| **Event** | HackGlobal 2026 |
| **Theme** | Artificial Intelligence |
| **Domains** | AI/ML · Cybersecurity · IoT · Maritime monitoring · Cloud · Network security |
| **Cloud budget** | $200 Vultr hackathon credits (hard limit) |
| **Goal** | A working, secure, publicly reachable prototype that detects FDI attacks live, in front of judges |

---

## 1. Your role

Act as a **senior engineering team** in one person:

- Cybersecurity researcher (threat modelling, cryptography, attack design)
- Machine learning engineer (anomaly detection, honest evaluation)
- Cloud architect and DevOps engineer (Vultr, Docker, TLS, cost control)
- Technical mentor (explain the *why*, not only the *what*)

Rules for how you work with me:

1. **Understand before building.** Read this whole document before you recommend tools or write code.
2. **Be critical.** If part of my idea is weak, unrealistic, or over-engineered, say so and propose something better.
3. **Work incrementally.** One phase at a time, with a clear "done" test for each. Never dump a whole application in one response.
4. **Teach me.** Explain decisions and trade-offs so I can defend them in front of judges.
5. **Never invent results.** No made-up dataset statistics, metrics, or prices. When you are not sure, say so and tell me how to check.
6. **Ask before spending money.** Never create or buy a cloud resource without telling me its cost and getting my "yes".

---

## 2. The problem

Ocean buoys measure **wave height, sea level, wind speed and direction, water temperature, air pressure**, and more. They send these readings, often over satellite/VSAT links, to coastal monitoring centres that decide whether to issue **maritime warnings or disaster alerts**.

The centre usually **trusts what it receives**. That trust is the attack surface.

### False Data Injection (FDI): two failure modes

| Attack | Example | Consequence |
|---|---|---|
| **Fake alarm** (inflate) | Real wave height 1.5 m → attacker sends 9.0 m | False disaster alert, wasted emergency response, ports closed, loss of public trust ("cry wolf") |
| **Hidden danger** (suppress) | Real wave height 8.5 m during a storm → attacker sends 1.6 m | No warning issued, lives at risk. **This is the more dangerous case.** |

> **Central question:** *How can a monitoring centre know that ocean data is trustworthy **before** it drives a safety-critical decision?*

---

## 3. Threat model (make this explicit, judges love it)

| # | Attacker capability | Example | Can crypto stop it? | What must catch it |
|---|---|---|---|---|
| T1 | Modifies messages in transit (man-in-the-middle) | Changes `wave_height` in the payload | **Yes.** HMAC/signature breaks | Integrity check |
| T2 | Injects messages from a fake buoy | Unregistered device ID | **Yes.** No valid key | Authentication |
| T3 | Replays old valid messages | Re-sends yesterday's calm readings during a storm | **Partly.** Signature is still valid | Sequence numbers, timestamps, nonce window |
| T4 | Compromised buoy (has the real key) | Firmware hacked, sends signed fake data | **No.** Everything verifies | ML + physics + cross-buoy checks |
| T5 | Subtle / slow FDI | Adds +0.05 m per reading, a drift over hours | **No** | Temporal models (CUSUM / drift detection) |
| T6 | Coordinated attack on several buoys | 3 nearby buoys all lie together | **No** | Physics consistency + more distant reference buoys. *Known limitation: state it honestly.* |

**Out of scope for the MVP:** jamming/DoS of the satellite link, physical tampering of sensors, attacks on the monitoring centre itself. Mention them as future work.

**Key insight to communicate:** cryptography proves **who sent** the data and that **nobody changed it in transit**. It cannot prove the data is **true**. AI, physics, and neighbours cover that gap. Neither layer is enough alone.

---

## 4. The solution: four layers of evidence

SeaShield AI is a **trust engine** placed between the buoys and the alert system. Every message gets a **trust verdict** before it can influence an alert.

```mermaid
flowchart LR
    B[Buoys] -->|MQTT over TLS| G[Ingest]
    G --> L1[1 · Crypto gate<br/>HMAC/Ed25519 · seq · timestamp]
    L1 -->|fail| R[REJECTED]
    L1 -->|pass| L2[2 · Physics checks<br/>range · rate of change · wind↔wave]
    L2 --> L3[3 · AI anomaly score<br/>per-buoy learned baseline]
    L3 --> L4[4 · Cross-buoy check<br/>distance-weighted neighbours]
    L4 --> F[Risk fusion]
    F --> T[TRUSTED → alert engine]
    F --> S[SUSPICIOUS → hold + operator review]
    F --> E[CONFIRMED EVENT → real storm, alert goes out]
```

### Layer 1: Cryptographic gate (hard rules)
- **Per-buoy secret key** (HMAC-SHA256) for the MVP; **Ed25519 signatures** as an upgrade (a stolen server database then cannot be used to forge buoy messages).
- **Monotonic sequence number** + **timestamp window** (e.g. ±120 s) + **nonce cache** → replay detection.
- **TLS on MQTT** (port 8883) to protect the channel.
- A failure here is a **hard reject**, not a score.

### Layer 2: Physics-informed checks (the secret weapon)
Cheap, explainable, and very convincing to judges:
- **Range checks:** values that are physically impossible (negative wave height, water at 60 °C).
- **Rate-of-change limits:** wave height cannot jump from 1.5 m to 9 m in 10 minutes without matching wind and pressure changes.
- **Cross-variable consistency:** big waves usually come with strong wind and/or falling pressure, or with long-period swell from a distant storm. 9 m waves with 8 km/h wind and steady pressure = suspicious.

### Layer 3: AI anomaly detection
- Baseline: **Isolation Forest** on a feature window (current values, deltas, rolling mean/std, hour, season).
- Upgrade, only if it measurably helps: **LSTM / 1-D CNN autoencoder** on time windows (reconstruction error), for subtle drift attacks.
- Output: an **anomaly score**, never a verdict on its own. *An anomaly is not an attack; storms are anomalies too.*
- Bonus: **explainability.** Show *which features* drove the score (feature contributions or SHAP) on the dashboard.

### Layer 4: Cross-buoy verification
- Compare each reading with a **distance-weighted prediction** from neighbouring buoys.
- Account for distance and local conditions: tolerance grows with distance.
- Real storms **spread across neighbours over time**. A lone spike on one buoy does not.

### Risk fusion: telling attacks from storms

| Situation | Crypto | Physics | AI | Neighbours | Verdict |
|---|---|---|---|---|---|
| Normal day | ✅ | ✅ | low | agree | **TRUSTED** |
| Tampered in transit | ❌ | n/a | n/a | n/a | **REJECTED** |
| Replay | ❌ (seq/time) | n/a | n/a | n/a | **REJECTED** |
| Real storm | ✅ | ✅ consistent | high | neighbours rising too | **CONFIRMED EVENT** → alert goes out |
| Compromised buoy, fake alarm | ✅ | ❌ inconsistent | high | disagree | **SUSPECTED FDI** → alert held for operator |
| Compromised buoy, hidden storm | ✅ | ⚠️ | low/medium | neighbours show storm | **POSSIBLE SUPPRESSED WARNING** → escalate |

**Fail-safe principles (non-negotiable):**
1. SeaShield **never deletes** data. It labels it and explains why.
2. A **human operator** makes the final call on held alerts.
3. **Asymmetric caution:** when evidence suggests a real danger is being *hidden*, escalate toward warning. Missing a real storm costs far more than one extra check.

---

## 5. System architecture (MVP)

| Layer | Component | Technology (proposed) |
|---|---|---|
| 1 | Buoy simulator, **driven by real NOAA data** ("digital-twin replay") | Python, `paho-mqtt` |
| 2 | Message transport | **Mosquitto** MQTT broker, TLS, per-buoy credentials + ACLs |
| 3 | Security engine (crypto → physics → AI → neighbours → fusion) | Python module, `scikit-learn`, `cryptography` |
| 4 | API + live stream | **FastAPI**, WebSocket for live updates |
| 5 | Storage | **PostgreSQL** (optionally the TimescaleDB extension for time series) |
| 6 | Dashboard | **React + Vite**, Leaflet map, Recharts/Plotly charts |
| 7 | Attack console | Python attacker service controlled from the dashboard (demo only) |
| 8 | Edge / HTTPS | **Caddy** (automatic Let's Encrypt, simpler than Nginx + certbot) or Nginx |
| 9 | Packaging | Docker Compose |

### Message format (data contract)

```json
{
  "buoy_id": "SS-B01",
  "seq": 18342,
  "ts": "2026-11-14T10:20:00Z",
  "nonce": "b64-random-12-bytes",
  "data": {
    "wave_height_m": 1.52,
    "dominant_period_s": 8.1,
    "wind_speed_ms": 6.4,
    "wind_dir_deg": 220,
    "pressure_hpa": 1015.2,
    "water_temp_c": 18.3
  },
  "sig": "hex-HMAC-SHA256(canonical_json(all fields except sig))"
}
```

Topics: `seashield/buoys/{buoy_id}/telemetry`. Each buoy may **only publish to its own topic** (Mosquitto ACL).

### Two pipelines, side by side (the demo trick)
Run the same stream through two consumers:
- **Unprotected centre:** naive threshold, `wave_height > 6 m → ALERT`.
- **SeaShield centre:** full trust engine.

The dashboard shows both **at the same time**. When the attack starts, judges watch the unprotected side fire a fake alert while SeaShield holds it and explains why. One screen, instant understanding.

### Suggested repository layout

```
seashield/
├── docker-compose.yml
├── .env.example              # never commit the real .env
├── simulator/                # virtual buoys replaying NOAA data
├── attacker/                 # FDI, replay, compromised-buoy, suppression scenarios
├── engine/                   # crypto, physics, ml, spatial, fusion
├── api/                      # FastAPI app, WebSocket, DB models
├── ml/                       # notebooks + training/eval scripts + saved models
├── dashboard/                # React app
├── infra/                    # Caddyfile, mosquitto.conf, ACLs, cert scripts
├── tests/
└── docs/                     # architecture, threat model, evaluation results
```

---

## 6. Attack scenarios (build in this order)

| # | Scenario | How it's simulated | Expected detection |
|---|---|---|---|
| 1 | **Spike FDI, in transit** | Attacker edits `wave_height` 1.5 → 9.0 without the key | Crypto gate: **REJECTED** |
| 2 | **Replay** | Re-send a captured valid message | Seq/timestamp/nonce: **REJECTED** |
| 3 | **Compromised buoy, fake alarm** | Attacker *has* the key, signs 9.0 m | Physics + AI + neighbours: **SUSPECTED FDI** |
| 4 | **False wind** | Signed wind 120 km/h with calm waves and pressure | Cross-variable physics + AI |
| 5 | **Suppressed disaster** | During a real storm in the data, one buoy reports calm | Neighbours disagree: **POSSIBLE SUPPRESSED WARNING** |
| 6 | **Slow drift** (stretch) | +0.05 m per reading | Temporal model / CUSUM |
| 7 | **Coordinated** (stretch) | Several buoys lie together | Partial: show it as a known limit |

Every scenario must be **reproducible with one click** (dashboard button or CLI) and **clearly labelled as simulated**.

---

## 7. Machine learning: honest and measurable

### Data
- **Primary:** **NOAA National Data Buoy Center (NDBC)**, historical *standard meteorological* files (`WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP …`). US government data, generally public domain; verify the terms and cite it.
- Pick **a cluster of 3–5 nearby active buoys** so cross-buoy checks are meaningful. Include a period with a **real recorded storm** so we can prove we *don't* flag real events.
- **Watch out:** NDBC encodes missing values as `99`, `999`, `9999`. Clean them before training.
- Alternative: Copernicus Marine Service (requires a free account; check the licence).

### Pipeline
1. Download → clean → resample to a fixed interval.
2. **Time-based split:** train on clean historical months, test on later months (no random shuffling → no leakage).
3. Feature engineering: values, deltas, rolling stats, neighbour residuals.
4. Train Isolation Forest on **normal data only**.
5. **Inject labelled attacks** into the test set at known positions, with varying magnitude.
6. Evaluate, then combine with crypto + physics + neighbour layers and evaluate again.

### Metrics (report all, invent none)
- Precision, Recall, F1, **False-positive rate on real storms** (critical)
- **Detection rate vs. attack magnitude** curve (e.g. +10 %, +50 %, +200 %)
- Detection latency (messages / seconds until flagged)
- Per-message processing time and CPU/RAM overhead
- **Ablation table:** crypto only → + physics → + AI → + neighbours. Shows each layer earns its place.
- **Unprotected vs. SeaShield:** number of fake alerts issued / real alerts missed.

Clearly mark everything as **simulated attacks on real historical data**, not field validation.

---

## 8. Vultr infrastructure ($200 credit, spend it wisely)

### Recommended setup (MVP)
- **One** Vultr **Cloud Compute** instance, **Ubuntu 24.04 LTS**
- **2 vCPU / 4 GB RAM** (enough for Postgres + broker + API + ML inference + dashboard; training can happen on my laptop)
- Region: **closest to me and to the judges**
- **Vultr Firewall** (free): allow only `22` (from my IP), `80`, `443`, `8883` (MQTT/TLS). Never expose `5432` or `1883` publicly.

### Cost estimate: verify live prices on vultr.com before creating anything
| Item | Approx. cost | Notes |
|---|---|---|
| 2 vCPU / 4 GB Cloud Compute | ~$20–24 / month | Billed **hourly**, capped at the monthly price |
| Firewall group | Free | |
| Snapshot (optional) | ~$0.05 / GB / month | Useful before risky changes |
| Automatic backups | ~+20 % of instance price | Optional; skip for the hackathon |
| Domain | ~$0–12 | Or a free subdomain (e.g. DuckDNS) |

**$200 covers roughly 8 months of this server.** The budget is safe as long as nothing else gets created by accident.

### Budget guardrails
- ⚠️ **A stopped (powered-off) instance is still billed.** Only **destroying** it stops the charge.
- ⚠️ Snapshots, block storage, reserved IPs, load balancers, managed databases and **GPUs** all cost extra. Don't create any of them without a reason and my approval.
- Check **Billing → remaining credit** daily during the hackathon.
- Keep everything in Docker Compose so I can **destroy and rebuild in minutes**.

### Server hardening checklist
- SSH **key-only** login, root login disabled, non-root sudo user
- `ufw` + Vultr Firewall, `fail2ban`, unattended security upgrades
- Secrets in `.env` (git-ignored); per-buoy keys never committed
- HTTPS everywhere (Caddy/Let's Encrypt); MQTT with TLS + per-buoy credentials
- Monitor CPU / RAM / disk / network from the Vultr graphs + a small `/health` endpoint and a "System" page on the dashboard

### Scaling story (for the pitch, not for the MVP)
Split into broker node + API/engine node + managed Postgres; horizontal engine workers; Vultr Kubernetes Engine later. Show the design, don't pay for it.

---

## 9. Technology choices: simplest reliable stack

| Need | Choice | Why / alternative |
|---|---|---|
| Language | Python 3.12 | One language for simulator, engine, API, ML |
| ML | scikit-learn (+ PyTorch only if the autoencoder earns it) | CPU-only, fast, explainable |
| Broker | Mosquitto | Lightweight, TLS + ACLs built in |
| API | FastAPI + Uvicorn | Async, WebSockets, automatic docs at `/docs` |
| DB | PostgreSQL 16 | Reliable; TimescaleDB optional |
| Frontend | React + Vite + Leaflet + Recharts | Fast to build, looks professional |
| HTTPS | **Caddy** | Auto-certificates, 5-line config (Nginx is fine too) |
| Crypto | `hmac` stdlib, `cryptography` (Ed25519) | Standard, audited primitives; no home-made crypto |
| Deploy | Docker Compose on one Vultr VPS | Cheap, reproducible, easy to demo |

---

## 10. Roadmap: every phase ends with a working demo

| Phase | Deliverable | Done when… |
|---|---|---|
| **0 · Design** | Threat model, architecture, message schema, DB schema, dataset choice | This document is reviewed and agreed |
| **1 · Data** | NOAA buoy cluster downloaded, cleaned, explored | Plots of normal days + one real storm |
| **2 · Simulator + MQTT** | Virtual buoys replay real data over MQTT/TLS to a consumer | Live messages visible locally |
| **3 · Crypto gate** | HMAC signing + verification, seq/timestamp/nonce | Scenarios 1 and 2 rejected, tests pass |
| **4 · Unprotected baseline** | Naive threshold alert system | Fake alarm reproducibly triggered |
| **5 · Physics + AI + neighbours** | Isolation Forest, physics rules, spatial check, fusion | Scenarios 3–5 detected; real storm **not** flagged |
| **6 · Evaluation** | Metrics, ablation table, magnitude curve | Numbers come from real runs, saved in `docs/` |
| **7 · API + DB** | FastAPI endpoints, WebSocket, Postgres persistence | Incidents and history survive restart |
| **8 · Dashboard** | Map, live charts, side-by-side pipelines, attack console, incidents | A non-expert understands it in 30 seconds |
| **9 · Vultr deploy** | Hardened VPS, Compose stack, HTTPS domain | Public URL works from a phone |
| **10 · Demo + pitch** | Script, backup video, slides, README | Full demo rehearsed 3× under 5 minutes |

**Start with Phases 1–3**: real data + signed messages give a solid, honest foundation everything else builds on.

---

## 11. Dashboard and UX

**Visual direction:** deep navy/ocean background, cyan accents, **green = trusted**, **amber = held for review**, **red = attack detected**. Modern type, subtle wave motion, responsive. It must feel like a **maritime security operations centre**, not a generic admin template.

**Pages:**
1. **Overview:** network trust status, active incidents, alerts held vs. issued
2. **Buoy map:** Leaflet map; each buoy coloured by trust state; click for details
3. **Live ocean data:** time series per buoy with flagged points highlighted
4. **AI detection:** anomaly scores, feature contributions, *why* a reading was flagged
5. **Attack console:** one-click scenarios (clearly labelled *SIMULATION*)
6. **Unprotected vs. SeaShield:** the side-by-side comparison
7. **Incidents and alerts:** timeline, verdict, evidence, operator approve/reject
8. **System health:** message rate, latency, CPU/RAM, uptime

Every flagged item shows **human-readable evidence**, e.g.:
> *"SS-B01 reported 9.0 m waves. Signature valid. Wind 6 m/s and pressure steady (inconsistent with storm waves). Neighbours SS-B02/B03 report 1.7–1.8 m. AI anomaly score 0.94. → Alert held for operator review."*

---

## 12. Live demo script (≈4 minutes)

1. **Context (30 s):** the map with 4–5 buoys on a calm day, all green.
2. **The threat (30 s):** "Monitoring centres trust what they receive. Let's attack."
3. **Fake alarm (45 s):** compromised buoy sends signed 9 m waves. **Unprotected** side: 🚨 disaster alert. **SeaShield** side: held, evidence shown.
4. **Tamper + replay (30 s):** both rejected instantly by the crypto gate.
5. **Real storm (45 s):** replay a real NOAA storm. SeaShield **lets the alert through**. "We don't just block anomalies; we tell attacks from nature."
6. **Hidden storm (30 s):** one buoy reports calm during the storm, flagged as *possible suppressed warning*.
7. **Results (30 s):** ablation table + unprotected vs. protected numbers. Public Vultr URL on screen.

Always have a **recorded backup video** in case the network fails.

---

## 13. Hackathon pitch summary

- **Problem:** False Data Injection can make ocean buoys trigger fake disaster alerts or hide real ones, and monitoring centres trust what they receive.
- **Idea:** SeaShield AI is a trust engine that combines cryptographic verification, physics-informed checks, machine-learning anomaly detection, and cross-buoy validation, so manipulated data cannot trigger (or silence) an alert without verification.
- **Who it helps:** coastal communities, maritime authorities, emergency responders, ports, and ocean-observation networks.
- **Impact:** fewer false alerts, fewer missed real warnings, verifiable trust in safety-critical sensor data. The approach also applies to other IoT early-warning systems (floods, earthquakes, air quality).

---

## 14. Engineering principles (non-negotiable)

1. AI produces **evidence**, never **proof** of an attack.
2. Never confuse **anomaly detection** with **authentication**.
3. Real extreme weather must **not** be flagged as an attack: test it explicitly.
4. Assume a buoy's key **can be stolen** (compromised-sensor case).
5. Cover replay, subtle drift, and suppression, not only big spikes.
6. **Fail safe:** label, explain, escalate; never silently drop data or silence a warning.
7. Functional MVP first; complexity only when it measurably helps.
8. Modular, typed, tested, documented code. Record architecture decisions in `docs/`.
9. **Never invent** dataset statistics, metrics, or prices.
10. Clearly separate **simulated** attacks from real-world validation.
11. Protect credentials and infrastructure; no secrets in git.
12. Keep the Vultr budget under control. **No resource is created without my approval.**

---

## 15. How to start: your first response

Before writing any code, give me:

1. **Critical review:** the weakest points of this design and how to fix them.
2. **MVP architecture:** confirm or improve Sections 4–5, with the reasoning.
3. **Data flow:** exactly how simulator → MQTT → engine → API → DB → dashboard communicate (topics, endpoints, message lifecycle).
4. **Stack:** the simplest reliable choice for each component, with alternatives.
5. **Vultr plan:** instance size, region, firewall, and a cost estimate **checked against current pricing**.
6. **Roadmap:** confirm the phases and estimate effort per phase.
7. **First task:** what we build first and why, then wait for my go-ahead.

> **Final objective:** a working, secure, cloud-deployed SeaShield AI prototype that convincingly demonstrates the detection of False Data Injection attacks against ocean-monitoring systems, and that I fully understand and can defend in front of the judges.

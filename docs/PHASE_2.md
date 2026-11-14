# Phase 2: Buoy Simulator over MQTT (report)

**Date:** 2026-11-14
**Status:** ✅ Complete (live end-to-end test passed on a local broker; Docker run pending a Windows fix, see §5)
**Plan reference:** [`PLAN.md` → Phase 2](PLAN.md#phase-2-buoy-simulator-over-mqtt---34-h)

---

## 1. Goal

The 4 virtual buoys replay **real NOAA data** as **signed messages over MQTT**; the security
engine receives and assesses every message and publishes its verdicts.

---

## 2. What was done, step by step

### Step 0: Signed `observed_at` field (decision 0003)
- `Telemetry` now has two clocks: **`ts`** (send time → replay protection) and
  **`observed_at`** (measurement time → physics). Both are covered by the HMAC signature.
- Test: changing `observed_at` breaks the signature (`test_observed_at_is_signed`).

### Step 1: Physics layer uses observation time, with per-hour limits
- `PhysicsChecker.check(buoy, observed_at, m, sent_at)`. Rates are computed over
  `observed_at`, never the send time.
- Rate limits converted to **per hour**, set from the largest real hourly changes in
  3 years of data (`data-notes.md` §5) plus a margin:

| Field | Max real change in 1 h | Limit |
|---|---|---|
| Wave height | 2.905 m (SS-B03, Idalia) | **3.5 m/h** |
| Wind speed | 11.8 m/s (SS-B04) | **15 m/s/h** |
| Pressure | 15.35 hPa (SS-B01, Helene) | **20 hPa/h** |
| Water temp | 1.6 °C (SS-B03) | **3 °C/h** |

- New timing rules: `observed_at` must **increase** per buoy, and may not be later than the
  send time + 120 s.
- **Verified on real data:** the new rules flag **0 of 94,458 real hours** (all 4 buoys,
  2023–2025, all storms included), yet catch a 1.5 → 9.0 m jump between two hourly readings.

### Step 2: Replay source (`seashield/simulator/replay.py`)
- All buoys share **one historical clock**, so storms cross the network as they really did.
- Each buoy reports **only its own sensors** (`sensors` in `config/buoys.yaml`).
- An hour in which a buoy has no data produces **no message**, just like a real buoy that goes
  offline in a storm.

### Step 3: Simulator CLI (`python -m seashield.simulator`)
| Option | Meaning |
|---|---|
| `--start`, `--end` | historical window (e.g. Helene: `--start 2024-09-25T12:00 --end 2024-09-27T12:00`) |
| `--interval` | seconds per historical hour (default 2 s → a 3-day storm in ~2.5 min) |
| `--hours` | stop after N historical hours |
| `--reset` | demo/operator: ask the engine to forget physical history before a new scenario |

QoS 1 publishing; one log line per historical hour showing which buoys are offline.

### Step 4: Restart-safe sequence numbers (bug found by a test)
- First version: `seq` started from the clock in **milliseconds**, assuming < 1 message/ms.
  The new test sent a **burst** (as one tick does: 4 buoys at once) → after an immediate restart,
  the new `seq` was **lower** than the last one sent → it would be rejected as a replay.
- Fix: `seq = max(previous + 1, now in µs)`. Strictly increasing, follows the clock, restart
  starts above every previous number. ≈ 1.8 × 10¹⁵ < 2⁵³, so it is exact in JavaScript too.
- The live run also showed why the max is needed: two buoys built in the same clock tick
  got the same µs value (Windows clock resolution). Per-buoy counters still increase.

### Step 5: MQTT helpers + engine
- `connect_with_retry()`: services wait for the broker instead of crashing (Docker start order).
- Engine re-subscribes on every (re)connect, logs both clocks, publishes each `Assessment` to
  `seashield/verdicts/<buoy>`, and prints running totals (verdicts + unprotected alerts).

### Step 6: Broker
- `docker-compose.yml`: Mosquitto published on **127.0.0.1:1883 only** (this machine, never the network).
- **Docker could not start on this PC** (§5). To avoid blocking, a pure-Python dev broker was
  added: **amqtt** (`infra/dev/amqtt.yaml`, bound to 127.0.0.1, dev dependency).
  Production still uses Mosquitto.

### Step 7: Live end-to-end test (problem found → operator reset)
First live run: Helene, then the simulator was restarted on a calm week (May 2024):
- ✅ restart: **0 replay rejections** (Step 4 works live)
- ⚠️ but **36 of 48** calm-week messages were `SUSPECTED_FDI`: *"observation time 2024-05-06
  not after previous 2024-09-27"*. The engine remembered Helene, and the demo jumped **back**
  in historical time. In real operation time never goes back, so the rule is right; a demo
  that switches scenarios needs a way to clear that memory.
- A buoy must **never** be able to wipe the engine's memory (that would be an attack path), so this
  is an **operator** action: topic `seashield/control/reset` →
  `SecurityPipeline.reset_history()` clears physics + spatial history and **keeps replay
  protection** (sequence numbers and nonces). The Mosquitto ACL allows only the `operator`
  identity to write `seashield/control/#`.
- Test: `test_operator_reset_clears_history_but_keeps_replay_protection`.

**Final live run** (local broker, engine, simulator, verdict listener as 4 separate processes):

| Run | Messages | Engine verdicts | Unprotected alerts | Verdicts received over MQTT |
|---|---|---|---|---|
| Helene, 2024-09-25 12:00 → 09-27 12:00 | 137 | **137 TRUSTED** | **13** `HIGH_WAVES` | 137 |
| Restart + `--reset`, calm week, 24 h | 96 | **96 TRUSTED** | 0 | 96 |
| **Total** | **233** | **233 TRUSTED** (0 rejected, 0 suspected) | 13 | **233** |

- Helene alerts appear first at SS-B02 (from 13:00) and at SS-B01 from 21:00, the storm
  moving north, as in the real data. SS-B03 was offline during the whole window (real outage);
  SS-B04 sent 39 instead of 49 messages (real outage after the peak).
- These 13 alerts are **correct**: Helene was real. Showing *fake* alerts from the unprotected
  centre is Phase 3/4 (attacks).

---

## 3. Tests

| File | New tests |
|---|---|
| `tests/test_physics.py` | hourly spike flagged · largest real change allowed · rates use observation time, not send time · longer gap allows larger change · time going backwards flagged · observation in the future flagged |
| `tests/test_replay.py` | shared clock + offline hours · only own sensors · start/end window · `observed_at` signed · restart-safe seq (burst) · **real Helene replay through signing + full pipeline: 0 rejected, 0 suspected, naive alerts > 0** |
| `tests/test_pipeline.py` | operator reset clears history, replay still rejected |

**Result: 41 passed**, ruff clean.

---

## 4. How to run it yourself

Terminal 1 (broker, no Docker needed):
```powershell
.venv\Scripts\activate
amqtt -c infra/dev/amqtt.yaml
```
Terminal 2 (engine):
```powershell
.venv\Scripts\activate
$env:SEASHIELD_MQTT_HOST="localhost"; python -m seashield.engine
```
Terminal 3 (simulator: Hurricane Helene in ~50 s):
```powershell
.venv\Scripts\activate
$env:SEASHIELD_MQTT_HOST="localhost"
python -m seashield.simulator --start 2024-09-25T12:00 --end 2024-09-27T12:00 --interval 1
python -m seashield.simulator --start 2024-05-06 --hours 24 --interval 0.5 --reset   # calm week
```
With Docker working: `docker compose up -d mosquitto` replaces terminal 1.

---

## 5. Open issue: Docker Desktop does not start on this PC

Docker Desktop's log says:
`engine linux/wsl failed to start: checking preconditions: Virtual Machine Platform not enabled`.
A hypervisor is already running on this PC, so CPU virtualization appears enabled; the missing
piece is the Windows feature. **Fix (admin PowerShell, then reboot):**
```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```
Not changed automatically: it is a system setting that needs administrator rights and a reboot.
Docker is **not required** until Phase 7 locally. The Vultr server (Linux) runs Docker natively.

---

## 6. Differences from the plan

- Broker for the local test: **amqtt** instead of Mosquitto-in-Docker (Docker blocked, §5).
- Extra: per-hour physics limits from real data (planned for 5.1, needed now because
  `observed_at` changed the time base), timing rules, operator reset + ACL, `connect_with_retry`.
- Not done (belongs to later phases): Docker-compose run of engine/simulator, Mosquitto TLS.

---

## 7. Next: Phase 3 (attacker tool)

Implement `python -m seashield.attacker --scenario tamper|replay|spike ...` against the live
stream, record ground truth outside the messages, and check verdicts live
(tamper/replay → `REJECTED`, compromised spike → `SUSPECTED_FDI` while the unprotected centre fires).

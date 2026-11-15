"""Live hub: bridges MQTT (engine verdicts) to browsers, and runs the demo attack console.

- Subscribes to engine events (seashield/verdicts/#) and buoy telemetry (to capture real
  messages the attacker can tamper with or replay).
- Keeps the last events + counters for page loads, pushes new events to WebSockets.
- Launches SIMULATED attacks. Ground truth (which message was an attack) stays here and
  is attached to the event for display only; the engine never sees it.
"""

import asyncio
import json
import logging
import threading
import time
from collections import Counter, deque
from typing import Any

from seashield.attacker import scenarios
from seashield.common.mqtt import make_client
from seashield.common.registry import load_keys
from seashield.config import get_settings

log = logging.getLogger("seashield.api.live")

SCENARIOS: dict[str, dict[str, str]] = {
    "spike": {
        "title": "Hacked buoy fakes giant waves",
        "threat": "T4 compromised buoy (valid key)",
        "what": "The attacker controls the buoy and signs a fake +7.5 m wave reading.",
    },
    "suppress": {
        "title": "Hacked buoy hides the storm",
        "threat": "T4 compromised buoy (valid key)",
        "what": "The attacker reports a calm 1 m sea. Most dangerous during a real storm.",
    },
    "tamper": {
        "title": "Man-in-the-middle edits the data",
        "threat": "T1 tampering in transit",
        "what": "A real message is intercepted and its wave height changed to 9 m, without the key.",
    },
    "replay": {
        "title": "Replay an old message",
        "threat": "T3 replay",
        "what": "A previously captured, validly signed message is sent again.",
    },
}
ATTACK_COOLDOWN_S = 2.0


class LiveHub:
    def __init__(self) -> None:
        self.s = get_settings()
        self.events: deque[dict] = deque(maxlen=400)
        self.stats: Counter[str] = Counter()
        self._captured: dict[str, deque[dict]] = {}   # real telemetry per buoy
        self._pending: dict[tuple[str, int], str] = {}  # (buoy, seq) -> scenario (ground truth)
        self._forged: set[tuple[str, int, str]] = set()  # (buoy, seq, nonce) sent by us
        self._queues: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._last_attack = 0.0
        self._client = None
        try:
            self._keys = load_keys(self.s.keys_file)
        except FileNotFoundError:
            self._keys = {}
            log.warning("no buoy keys found: compromised-buoy attacks disabled")

    # ------------------------------------------------------------------ lifecycle
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        client = make_client(self.s, client_id="seashield-api-live")
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.connect_async(self.s.mqtt_host, self.s.mqtt_port)
        client.loop_start()  # paho reconnects automatically
        self._client = client

    def stop(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()

    # ------------------------------------------------------------------ MQTT side
    def _on_connect(self, client, _u, _f, reason_code, _p) -> None:
        client.subscribe(self.s.topic_verdicts.format(buoy_id="+"), qos=1)
        client.subscribe(self.s.topic_telemetry.format(buoy_id="+"), qos=1)
        log.info("live hub connected to MQTT (%s)", reason_code)

    def _on_message(self, _client, _u, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        if msg.topic.startswith("seashield/verdicts/"):
            self._on_event(payload)
        else:
            self._capture(payload)

    def _capture(self, raw: dict) -> None:
        key = (raw.get("buoy_id"), raw.get("seq"), raw.get("nonce"))
        with self._lock:
            if key in self._forged:
                return  # never treat our own forged messages as "real captured traffic"
            self._captured.setdefault(str(raw.get("buoy_id")), deque(maxlen=60)).append(raw)

    def _on_event(self, event: dict) -> None:
        with self._lock:
            attack = self._pending.pop((event.get("buoy_id"), event.get("seq")), None)
            event["simulated_attack"] = attack
            self.events.append(event)
            self.stats["messages"] += 1
            self.stats[f"verdict_{event.get('verdict')}"] += 1
            if event.get("unprotected_alert"):
                self.stats["unprotected_alerts"] += 1
            if event.get("seashield_alert"):
                self.stats[f"seashield_{event['seashield_alert']}"] += 1
            if attack:
                self.stats["attacks_seen"] += 1
                if event.get("verdict") != "TRUSTED":
                    self.stats["attacks_caught"] += 1
                if event.get("unprotected_alert"):
                    self.stats["fake_alerts_unprotected"] += 1
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._broadcast, event)

    def _broadcast(self, event: dict) -> None:
        for q in list(self._queues):
            if q.qsize() < 500:
                q.put_nowait(event)

    # ------------------------------------------------------------------ browser side
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    def snapshot(self, limit: int = 200) -> list[dict]:
        with self._lock:
            return list(self.events)[-limit:]

    def stats_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.stats)

    # ------------------------------------------------------------------ attacks
    def launch(self, scenario: str, buoy_id: str) -> dict[str, Any]:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario '{scenario}'")
        now = time.monotonic()
        if now - self._last_attack < ATTACK_COOLDOWN_S:
            raise RuntimeError("an attack was just launched, wait a moment")
        with self._lock:
            captured = list(self._captured.get(buoy_id, ()))
        if len(captured) < 2:
            raise LookupError(f"no live traffic captured from {buoy_id} yet (buoy offline?)")

        latest, oldest = captured[-1], captured[0]
        key = self._keys.get(buoy_id)
        if scenario in ("spike", "suppress") and key is None:
            raise LookupError("buoy key not available on this server")
        wave = (latest.get("data") or {}).get("wave_height_m")
        if scenario in ("spike", "suppress") and wave is None:
            raise LookupError(f"{buoy_id} has no wave sensor, choose another buoy")

        if scenario == "spike":
            forged = scenarios.compromised_spike(latest, key, value=round(wave + 7.5, 2))
        elif scenario == "suppress":
            forged = scenarios.suppress(latest, key, calm_wave_m=1.0)
        elif scenario == "tamper":
            # captured[-2]: its genuine verdict has surely arrived already, so the ground-truth
            # label cannot be attached to the genuine copy by mistake.
            forged = scenarios.tamper_in_transit(captured[-2], value=9.0)
        else:
            forged = scenarios.replay(oldest)

        with self._lock:
            self._forged.add((forged["buoy_id"], forged["seq"], forged["nonce"]))
            self._pending[(forged["buoy_id"], forged["seq"])] = scenario
            self.stats["attacks_launched"] += 1
        self._last_attack = now
        self._client.publish(self.s.topic_telemetry.format(buoy_id=buoy_id), json.dumps(forged), qos=1)
        log.info("SIMULATED attack %s on %s (seq %s)", scenario, buoy_id, forged["seq"])
        return {"launched": True, "scenario": scenario, "buoy_id": buoy_id, "seq": forged["seq"],
                "forged_values": forged.get("data")}


hub = LiveHub()

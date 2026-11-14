"""Simulator service: every buoy publishes one signed reading per interval (Phase 2).

Run:  python -m seashield.simulator
"""

import json
import logging
import time

from seashield.common.mqtt import make_client
from seashield.common.registry import load_buoys, load_keys
from seashield.config import get_settings
from seashield.simulator.buoy import VirtualBuoy
from seashield.simulator.replay import replay_station

log = logging.getLogger("seashield.simulator")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    s = get_settings()
    keys = load_keys(s.keys_file)
    buoys = load_buoys(s.buoys_file)

    fleet = []
    for b in buoys:
        if b.ndbc_station is None:
            log.warning("%s has no NDBC station yet (config/buoys.yaml), skipped", b.buoy_id)
            continue
        source = replay_station(f"data/processed/{b.ndbc_station}.parquet")
        fleet.append((VirtualBuoy(b.buoy_id, keys[b.buoy_id]), source))

    client = make_client(s, client_id="seashield-simulator")
    client.connect(s.mqtt_host, s.mqtt_port)
    client.loop_start()

    while fleet:
        for buoy, source in fleet:
            msg = buoy.build_message(next(source))
            client.publish(s.topic_telemetry.format(buoy_id=buoy.buoy_id), json.dumps(msg))
        time.sleep(s.publish_interval_s)
    log.error("no buoy configured; fill in config/buoys.yaml (Phase 1)")


if __name__ == "__main__":
    main()

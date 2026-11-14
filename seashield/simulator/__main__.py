"""Simulator service: the buoy network replays real NOAA data as signed MQTT messages.

One historical hour is replayed every `--interval` seconds (time compression), so a
3-day storm plays in ~2.5 minutes at the default 2 s.

Examples:
  python -m seashield.simulator                                    # all history, from the start
  python -m seashield.simulator --start 2024-05-06                 # a calm week
  python -m seashield.simulator --start 2024-09-25T12:00 --end 2024-09-27T12:00 --interval 1
                                                                   # Hurricane Helene in ~50 s
"""

import argparse
import json
import logging
import time

from seashield.common.mqtt import connect_with_retry, make_client
from seashield.common.registry import load_buoys, load_keys
from seashield.config import get_settings
from seashield.simulator.buoy import VirtualBuoy
from seashield.simulator.replay import replay

log = logging.getLogger("seashield.simulator")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SeaShield buoy network simulator (NOAA replay)")
    p.add_argument("--start", help="historical start time, e.g. 2024-09-25 or 2024-09-25T12:00")
    p.add_argument("--end", help="historical end time")
    p.add_argument("--interval", type=float, help="seconds between historical hours "
                   "(default SEASHIELD_PUBLISH_INTERVAL_S)")
    p.add_argument("--hours", type=int, help="stop after this many historical hours")
    p.add_argument("--data-dir", default="data/processed")
    p.add_argument("--reset", action="store_true",
                   help="DEMO/OPERATOR: ask the engine to forget physical history before a new "
                        "scenario (needed when jumping back in historical time)")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    args = parse_args()
    s = get_settings()
    interval = args.interval if args.interval is not None else s.publish_interval_s

    buoys = [b for b in load_buoys(s.buoys_file) if b.ndbc_station]
    if not buoys:
        raise SystemExit("no buoy has an ndbc_station in config/buoys.yaml (Phase 1)")
    keys = load_keys(s.keys_file)
    fleet = {b.buoy_id: VirtualBuoy(b.buoy_id, keys[b.buoy_id]) for b in buoys}

    client = make_client(s, client_id="seashield-simulator")
    connect_with_retry(client, s)
    client.loop_start()
    if args.reset:
        client.publish(s.topic_control_reset, b"reset", qos=1).wait_for_publish(timeout=5)
        log.info("operator reset sent to the engine")
        time.sleep(0.5)
    log.info("replaying %d buoys from %s, %.1f s per historical hour",
             len(fleet), args.start or "the beginning", interval)

    sent = 0
    try:
        for hour, tick in enumerate(replay(buoys, args.data_dir, args.start, args.end), start=1):
            for buoy_id, reading in tick.readings.items():
                msg = fleet[buoy_id].build_message(reading, observed_at=tick.observed_at)
                client.publish(s.topic_telemetry.format(buoy_id=buoy_id), json.dumps(msg), qos=1)
                sent += 1
            offline = sorted(set(fleet) - set(tick.readings))
            log.info("%s  sent=%d  offline=%s", tick.observed_at.isoformat(timespec="minutes"),
                     len(tick.readings), ",".join(offline) or "-")
            if args.hours and hour >= args.hours:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("stopped by user")
    finally:
        time.sleep(0.5)  # let QoS 1 messages flush
        client.loop_stop()
        client.disconnect()
        log.info("done, %d messages sent", sent)


if __name__ == "__main__":
    main()

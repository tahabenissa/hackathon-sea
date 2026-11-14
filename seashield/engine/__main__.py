"""Engine service: subscribe to buoy telemetry, assess every message (Phase 3-5).

Run:  python -m seashield.engine
"""

import json
import logging

from seashield.common.mqtt import make_client
from seashield.common.registry import load_buoys, load_keys
from seashield.config import get_settings
from seashield.engine.baseline import naive_alert
from seashield.engine.pipeline import SecurityPipeline

log = logging.getLogger("seashield.engine")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    s = get_settings()
    pipeline = SecurityPipeline(load_keys(s.keys_file), load_buoys(s.buoys_file), s.replay_window_s)

    def on_message(client, _userdata, msg) -> None:
        try:
            raw = json.loads(msg.payload)
        except json.JSONDecodeError:
            log.warning("non-JSON payload on %s", msg.topic)
            return
        unprotected = naive_alert(raw)
        result = pipeline.process(raw)
        log.info("%s seq=%s verdict=%s risk=%.2f unprotected_alert=%s | %s",
                 result.buoy_id, result.seq, result.verdict, result.risk, unprotected,
                 result.explanation)
        client.publish(s.topic_verdicts.format(buoy_id=result.buoy_id), result.model_dump_json())
        # TODO Phase 7: persist measurement + incident + both pipelines' alerts via the API/DB

    client = make_client(s, client_id="seashield-engine")
    client.on_message = on_message
    client.connect(s.mqtt_host, s.mqtt_port)
    client.subscribe(s.topic_telemetry.format(buoy_id="+"))
    log.info("engine listening on %s:%s", s.mqtt_host, s.mqtt_port)
    client.loop_forever()


if __name__ == "__main__":
    main()

"""Engine service: subscribe to buoy telemetry, assess every message.

Run:  python -m seashield.engine
"""

import json
import logging
from collections import Counter

from seashield.common.mqtt import connect_with_retry, make_client
from seashield.common.registry import load_buoys, load_keys
from seashield.config import get_settings
from seashield.engine.baseline import naive_alert
from seashield.engine.pipeline import SecurityPipeline

log = logging.getLogger("seashield.engine")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    s = get_settings()
    pipeline = SecurityPipeline(load_keys(s.keys_file), load_buoys(s.buoys_file), s.replay_window_s)
    verdicts: Counter[str] = Counter()
    baseline_alerts = 0

    def on_connect(client, _userdata, _flags, reason_code, _props) -> None:
        # (Re)subscribe on every connect, so a broker restart does not silently stop us.
        client.subscribe(s.topic_telemetry.format(buoy_id="+"), qos=1)
        client.subscribe(s.topic_control_reset, qos=1)
        log.info("connected to MQTT %s:%s (%s), listening", s.mqtt_host, s.mqtt_port, reason_code)

    def on_message(client, _userdata, msg) -> None:
        nonlocal baseline_alerts
        if msg.topic == s.topic_control_reset:
            pipeline.reset_history()
            log.info("OPERATOR RESET: physical history cleared (replay protection kept)")
            return
        try:
            raw = json.loads(msg.payload)
        except json.JSONDecodeError:
            log.warning("non-JSON payload on %s", msg.topic)
            return
        unprotected = naive_alert(raw)
        result = pipeline.process(raw)
        verdicts[result.verdict.value] += 1
        baseline_alerts += unprotected is not None
        log.info("%s seq=%s obs=%s verdict=%s risk=%.2f | unprotected_alert=%s | %s",
                 result.buoy_id, result.seq, raw.get("observed_at"), result.verdict, result.risk,
                 unprotected, result.explanation)
        client.publish(s.topic_verdicts.format(buoy_id=result.buoy_id), result.model_dump_json(),
                       qos=1)
        total = sum(verdicts.values())
        if total % 50 == 0:
            log.info("TOTALS after %d messages: %s | unprotected alerts: %d",
                     total, dict(verdicts), baseline_alerts)
        # TODO Phase 7: persist measurement + incident + both pipelines' alerts

    client = make_client(s, client_id="seashield-engine")
    client.on_connect = on_connect
    client.on_message = on_message
    connect_with_retry(client, s)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        log.info("stopped. TOTALS: %s | unprotected alerts: %d", dict(verdicts), baseline_alerts)


if __name__ == "__main__":
    main()

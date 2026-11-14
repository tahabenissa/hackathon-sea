from seashield.attacker import scenarios
from seashield.common.schema import Verdict
from seashield.engine.baseline import naive_alert
from seashield.engine.pipeline import SecurityPipeline


def test_normal_reading_trusted(buoy, calm, keys):
    result = SecurityPipeline(keys, buoys=[]).process(buoy.build_message(calm))
    assert result.verdict == Verdict.TRUSTED


def test_tampered_reading_rejected(buoy, calm, keys):
    forged = scenarios.tamper_in_transit(buoy.build_message(calm))
    result = SecurityPipeline(keys, buoys=[]).process(forged)
    assert result.verdict == Verdict.REJECTED


def test_compromised_spike_fools_baseline_but_not_seashield(buoy, calm, keys):
    pipeline = SecurityPipeline(keys, buoys=[])
    pipeline.process(buoy.build_message(calm))
    forged = scenarios.compromised_spike(buoy.build_message(calm), keys["SS-B01"])

    assert naive_alert(forged) == "HIGH_WAVES"          # unprotected centre: fake alarm
    assert pipeline.process(forged).verdict == Verdict.SUSPECTED_FDI

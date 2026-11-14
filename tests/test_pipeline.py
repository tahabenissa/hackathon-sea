from datetime import UTC, datetime

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


def test_operator_reset_clears_history_but_keeps_replay_protection(buoy, calm, keys):
    helene = datetime(2024, 9, 27, tzinfo=UTC)
    may = datetime(2024, 5, 6, tzinfo=UTC)
    pipeline = SecurityPipeline(keys, buoys=[])
    old = buoy.build_message(calm, observed_at=helene)
    assert pipeline.process(old).verdict == Verdict.TRUSTED

    # New demo scenario jumps back in historical time -> flagged without a reset
    assert pipeline.process(buoy.build_message(calm, observed_at=may)).verdict == Verdict.SUSPECTED_FDI

    pipeline.reset_history()
    assert pipeline.process(buoy.build_message(calm, observed_at=may)).verdict == Verdict.TRUSTED
    assert pipeline.process(old).verdict == Verdict.REJECTED   # a replay is still caught

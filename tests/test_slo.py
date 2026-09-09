"""Tests for Google SRE Error Budget & Burn Rate calculations."""
from kalman.telemetry.slo import SLOEngine


def test_slo_nominal_budget():
    engine = SLOEngine(target_slo=0.999)
    # 50 healthy ticks
    for _ in range(50):
        engine.record_sample(is_good_tick=True)

    report = engine.evaluate()
    assert report.current_availability_pct == 100.0
    assert report.burn_rate_1h == 0.0
    assert report.burn_status == "SAFE"
    assert report.error_budget_remaining_pct == 100.0


def test_slo_rapid_burn_on_degradation():
    engine = SLOEngine(target_slo=0.999)
    # Feed 20 bad ticks out of 100
    for _ in range(80):
        engine.record_sample(is_good_tick=True)
    for _ in range(20):
        engine.record_sample(is_good_tick=False)

    report = engine.evaluate()
    assert report.current_availability_pct == 80.0
    assert report.burn_rate_1h >= 14.4
    assert report.burn_status == "RAPID_BURN"
    assert report.bad_events_count == 20

"""Tests for the Predictive Forecaster."""
from kalman.agents.forecaster import Forecaster


def test_compute_slope_with_rising_trend():
    f = Forecaster(window_size=10)
    # Simulate rising value: 1.0, 2.0, 3.0 at t=0, 1, 2
    f.observe("cdn_5xx_rate", 1.0, timestamp=100.0)
    f.observe("cdn_5xx_rate", 2.0, timestamp=101.0)
    f.observe("cdn_5xx_rate", 3.0, timestamp=102.0)
    f.observe("cdn_5xx_rate", 4.0, timestamp=103.0)

    slope = f.compute_slope("cdn_5xx_rate")
    assert abs(slope - 1.0) < 1e-4


def test_seconds_to_threshold_rising():
    f = Forecaster()
    # Estimate = 20, slope = 2.0/s, threshold = 50 -> 15 seconds
    ttb = f.seconds_to_threshold(estimate=20.0, slope_per_s=2.0, threshold=50.0)
    assert ttb == 15.0


def test_seconds_to_threshold_no_breach_if_negative_slope():
    f = Forecaster()
    # Decreasing signal will not breach upper threshold
    ttb = f.seconds_to_threshold(estimate=20.0, slope_per_s=-1.5, threshold=50.0)
    assert ttb is None


def test_seconds_to_threshold_lower_bound():
    f = Forecaster()
    # Estimate = 0.9, slope = -0.05/s, lower threshold = 0.6 -> 6 seconds
    ttb = f.seconds_to_threshold(estimate=0.9, slope_per_s=-0.05, threshold=0.6, is_lower_bound=True)
    assert abs(ttb - 6.0) < 1e-4


def test_forecast_signal_imminent_breach():
    f = Forecaster()
    # Feed rising values heading for threshold=50 in ~10s
    for i in range(5):
        f.observe("cdn_5xx_rate", 30.0 + i * 2.0, timestamp=100.0 + i)

    proj = f.forecast_signal("cdn_5xx_rate", current_val=38.0, threshold=50.0, timestamp=104.0)
    assert proj.status in ("WATCH", "IMMINENT_BREACH")
    assert proj.seconds_to_breach is not None
    assert proj.seconds_to_breach < 20.0
    assert proj.risk_score > 50.0

"""Tests for Cross-Correlation and Blast Radius analysis."""
from kalman.detectors.correlation import CorrelationEngine


def test_pearson_correlation_identical_trends():
    engine = CorrelationEngine(window_size=20)
    # Perfectly coupled signals
    for i in range(10):
        engine.observe("sig_a", float(i))
        engine.observe("sig_b", float(i * 2))

    r = engine.compute_pearson("sig_a", "sig_b")
    assert abs(r - 1.0) < 1e-3


def test_blast_radius_initiator_identification():
    engine = CorrelationEngine()
    # Feed baseline observations
    for i in range(10):
        engine.observe("cdn_5xx_rate", 1.0)
        engine.observe("rebuffer_ratio", 0.005)

    # cdn_5xx_rate spikes first
    engine.record_spike("cdn_5xx_rate")
    engine.record_spike("rebuffer_ratio")

    anomalies = [
        {"signal": "cdn_5xx_rate", "value": 55.0},
        {"signal": "rebuffer_ratio", "value": 0.08},
    ]

    report = engine.analyze_incident(anomalies)
    assert report.initiator_signal == "cdn_5xx_rate"
    assert report.infrastructure_layer == "CDN_EDGE"
    assert report.is_systemic is True
    assert report.affected_audience_pct > 30.0

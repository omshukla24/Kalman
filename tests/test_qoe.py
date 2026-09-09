"""Tests for the ITU-T P.1203 QoE and MOS calculation engine."""
from kalman.telemetry.qoe import QoEEngine


def test_qoe_pristine_broadcast():
    engine = QoEEngine()
    # Nominal stream: 0.5% rebuffer, 1200ms join latency, 0.99 encoder health
    qoe = engine.compute_qoe(rebuffer_ratio=0.005, startup_latency_ms=1200.0, encoder_health=0.99)

    assert qoe.mos >= 4.0
    assert qoe.category in ("PRISTINE", "GOOD")
    assert qoe.viewer_abandonment_risk <= 0.05


def test_qoe_severe_rebuffer_degradation():
    engine = QoEEngine()
    # Severe rebuffer spike: 8% rebuffer
    qoe = engine.compute_qoe(rebuffer_ratio=0.08, startup_latency_ms=3500.0, encoder_health=0.50)

    assert qoe.mos < 2.5
    assert qoe.category in ("POOR", "UNACCEPTABLE")
    assert qoe.rebuffer_penalty > 2.0
    assert qoe.viewer_abandonment_risk > 0.40

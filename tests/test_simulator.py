"""Tests for Telemetry Simulator and Multi-Fault Scenarios."""
from kalman.telemetry import simulator


def test_emit_once_produces_snapshot_and_regional_matrix():
    snap = simulator.emit_once()
    assert "rebuffer_ratio" in snap
    assert "cdn_5xx_rate" in snap
    assert "encoder_health" in snap

    matrix = simulator.get_regional_matrix()
    assert "us-east" in matrix
    assert "eu-west" in matrix
    assert "rebuffer_ratio" in matrix["eu-west"]


def test_trigger_scenario_sets_regional_faults():
    res = simulator.trigger_scenario("cdn_meltdown", seconds=10.0)
    assert res["scenario"] == "cdn_meltdown"
    assert res["region"] == "eu-west"
    assert "cdn_5xx_rate" in res["signals"]

    # Call emit_once() to generate a snapshot with the new fault active
    simulator.emit_once()
    matrix = simulator.get_regional_matrix()
    eu_val = matrix["eu-west"]["cdn_5xx_rate"]
    # Baseline is ~1.0, with multiplier 35 it should be elevated
    assert eu_val > 5.0

    # Test remediation feedback reduces the fault
    simulator.apply_remediation_feedback("cdn_5xx_rate", factor=0.1)
    simulator.emit_once()
    matrix2 = simulator.get_regional_matrix()
    assert matrix2["eu-west"]["cdn_5xx_rate"] < eu_val

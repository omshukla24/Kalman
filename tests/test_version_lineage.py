"""Tests for Versioning, Regnal Coronation, and Lineage Manifest."""
from kalman.version import MAJOR_LINE, PATCH, full_version, lineage_manifest, regnal_name


def test_regnal_version_is_kalman_iii():
    assert MAJOR_LINE == 3
    assert regnal_name() == "KALMAN III"
    assert "0.3.0" in full_version()


def test_lineage_manifest_metadata():
    manifest = lineage_manifest()
    assert manifest["regnal_name"] == "KALMAN III"
    assert manifest["house"] == "House of Asura"
    assert len(manifest["chronicles"]) == 3
    assert len(manifest["crew"]) == 10

    crew_agents = [c["agent"] for c in manifest["crew"]]
    assert "Watcher" in crew_agents
    assert "Forecaster" in crew_agents
    assert "Diagnostician" in crew_agents
    assert "Governor" in crew_agents
    assert "Actuator" in crew_agents
    assert "Scribe" in crew_agents
    assert "Sentinel" in crew_agents
    assert "Economist" in crew_agents
    assert "Chronos" in crew_agents
    assert "Arbiter" in crew_agents

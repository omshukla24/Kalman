"""Tests for Diagnostician reasoning and Grafana query generation."""
import pytest
from kalman.agents.diagnostician import DiagnosticianRunner
from kalman.mcp.grafana_client import (
    execute_simulated_grafana_query,
    test_grafana_connection as check_grafana_health,
)


@pytest.mark.asyncio
async def test_diagnostician_diagnose_anomaly():
    diag = DiagnosticianRunner()
    anomaly = {
        "signal": "eu-west:cdn_5xx_rate",
        "region": "eu-west",
        "raw_signal": "cdn_5xx_rate",
        "value": 52.4,
        "predicted": 1.0,
        "z": 8.6,
        "severity": "P1_CRITICAL",
    }

    result = await diag.diagnose(anomaly)
    assert "incident_id" in result
    assert "root_cause" in result
    assert "eu-west" in result["root_cause"] or "cdn_5xx" in result["root_cause"]
    assert result["recommended_action"] == "shift_cdn_traffic"
    assert len(result["evidence"]) == 2
    assert len(result["query_ids"]) == 2
    assert all(e["query_id"] in result["query_ids"] for e in result["evidence"])


def test_simulated_grafana_query_returns_verifiable_id():
    res = execute_simulated_grafana_query("rate(kalman_rebuffer_ratio[1m])", signal="rebuffer_ratio", value=0.08)
    assert res["status"] == "success"
    assert res["query_id"].startswith("q-")
    assert res["result"]["value"] == 0.08
    assert len(res["result"]["correlated_logs"]) > 0


def test_grafana_connection_probe():
    status = check_grafana_health()
    assert "status" in status
    assert "mode" in status

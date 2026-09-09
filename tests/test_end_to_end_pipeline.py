"""End-to-end smoke tests for the complete KALMAN II pipeline.

Verifies:
  Telemetry Ingest -> Predictive Forecast -> Kalman Detection ->
  Diagnostician Reasoning -> Governor Policy -> Actuator Dispatch ->
  Autonomous Recovery Verification -> Grounded Scribe Postmortem.
"""
import asyncio
import pytest
from kalman.agents.orchestrator import Orchestrator
from kalman.agents.scribe import grounded


@pytest.mark.asyncio
async def test_full_pipeline_smoke():
    published = []

    def mock_sink(event: dict):
        published.append(event)

    orch = Orchestrator(publish=mock_sink)

    # 1. Warm up baseline (25 ticks)
    baseline_snapshot = {
        "rebuffer_ratio": 0.005,
        "cdn_5xx_rate": 1.0,
        "encoder_health": 0.99,
        "startup_latency_ms": 1200.0,
    }
    for _ in range(25):
        await orch.on_tick(baseline_snapshot)

    assert len(published) >= 25
    published.clear()

    # 2. Inject sustained fault (cdn_5xx_rate spike to 65.0)
    spike_snapshot = dict(baseline_snapshot)
    spike_snapshot["cdn_5xx_rate"] = 65.0

    for _ in range(4):
        await orch.on_tick(spike_snapshot)

    # Yield control to allow async _handle_incident tasks to finish
    await asyncio.sleep(0.1)

    event_types = [e["type"] for e in published]
    assert "telemetry" in event_types
    assert "anomaly" in event_types
    assert "diagnosis" in event_types
    assert "governance" in event_types
    assert "remediation" in event_types
    assert "postmortem" in event_types

    # Find the diagnosis and postmortem
    diagnosis_event = next(e for e in published if e["type"] == "diagnosis")
    postmortem_event = next(e for e in published if e["type"] == "postmortem")

    assert "root_cause" in diagnosis_event["diagnosis"]
    assert len(diagnosis_event["diagnosis"]["evidence"]) > 0

    pm_dict = postmortem_event["postmortem"]
    assert postmortem_event["grounded"] is True
    assert len(pm_dict["claims"]) > 0

    # 3. Simulate metric recovery post-actuator dispatch
    recovered_snapshot = dict(baseline_snapshot)
    for _ in range(3):
        await orch.on_tick(recovered_snapshot)

    recovery_events = [e for e in published if e["type"] == "recovery"]
    assert len(recovery_events) >= 1
    rec = recovery_events[0]
    assert rec["signal"] == "cdn_5xx_rate"
    assert rec["mttr_seconds"] is not None


@pytest.mark.asyncio
async def test_hitl_governance_approval_workflow():
    orch = Orchestrator(publish=lambda _: None)

    # Review destructive action
    d = orch.governor.review("failover_to_backup_stream", {"reason": "Test failover"})
    assert d.approved is False
    assert d.requires_human is True
    assert d.action_id is not None

    # Check pending list
    pending = orch.governor.get_pending_actions()
    assert len(pending) == 1
    assert pending[0]["action_id"] == d.action_id

    # Operator approves
    approval = orch.governor.approve_action(d.action_id, operator="Test_NOC_Lead")
    assert approval.approved is True
    assert "approved by Test_NOC_Lead" in approval.reason

    # Actuator dispatches
    exec_record = orch.actuator.dispatch(approval.action, approval.params)
    assert exec_record.status == "VERIFYING"

"""Tests for the Actuator remediation engine."""
from kalman.agents.actuator import Actuator


def test_actuator_dispatches_remediation_and_calls_feedback():
    feedback_calls = []

    def mock_hook(sig: str, factor: float):
        feedback_calls.append((sig, factor))

    act = Actuator(feedback_hook=mock_hook)
    execution = act.dispatch("shift_cdn_traffic", {"pct": 20}, target_signal="cdn_5xx_rate")

    assert execution.status == "VERIFYING"
    assert execution.action == "shift_cdn_traffic"
    assert len(feedback_calls) == 1
    assert feedback_calls[0] == ("cdn_5xx_rate", 0.2)


def test_actuator_recovery_verification():
    act = Actuator()
    execution = act.dispatch("throttle_bitrate_ladder", {"steps": 1}, target_signal="rebuffer_ratio")

    # High innovation -> not yet recovered
    assert act.check_recovery(execution.execution_id, current_z=6.5) is False
    assert execution.status == "VERIFYING"

    # Normalized innovation (|z| < 2.0) -> verified recovered!
    assert act.check_recovery(execution.execution_id, current_z=1.1) is True
    assert execution.status == "COMPLETED"
    assert execution.completed_at is not None
    assert execution.mttr_seconds is not None
    assert execution.mttr_seconds >= 0.0


def test_actuator_rollback():
    act = Actuator()
    execution = act.dispatch("scale_edge_capacity", {"nodes": 4})

    assert act.rollback(execution.execution_id) is True
    assert execution.status == "ROLLED_BACK"

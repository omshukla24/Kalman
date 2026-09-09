"""Tests for Automated Runbook Choreographer."""
from kalman.agents.runbook import RunbookChoreographer


def test_runbook_execution_and_step_advancement():
    choreographer = RunbookChoreographer()
    rb = choreographer.start_cdn_remediation_runbook("inc-cdn-99", region="eu-west")

    assert rb.status == "IN_PROGRESS"
    assert len(rb.steps) == 4
    assert rb.current_step == 0

    # Step 1 advance
    s1 = choreographer.advance_step(rb.runbook_id)
    assert s1 is not None
    assert s1.status == "COMPLETED"
    assert rb.current_step == 1

    # Advance remaining steps
    choreographer.advance_step(rb.runbook_id)
    choreographer.advance_step(rb.runbook_id)
    s4 = choreographer.advance_step(rb.runbook_id)

    assert s4 is not None
    assert rb.status == "COMPLETED"
    assert rb.completed_at is not None

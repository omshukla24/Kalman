"""Tests for AI Observability & Token Economics."""
from kalman.telemetry.ai_observability import AIObservability


def test_ai_observability_recording_and_cost():
    obs = AIObservability()

    # Flash call
    rec1 = obs.record_call(
        agent="watcher",
        model="gemini-flash-latest",
        prompt_tokens=1000,
        candidate_tokens=500,
        latency_ms=120.0,
    )
    assert rec1.total_tokens == 1500
    assert rec1.estimated_cost_usd > 0.0

    # Pro call
    rec2 = obs.record_call(
        agent="diagnostician",
        model="gemini-pro-latest",
        prompt_tokens=2000,
        candidate_tokens=1000,
        latency_ms=450.0,
    )
    assert rec2.total_tokens == 3000

    summary = obs.summary()
    assert summary["total_tokens"] == 4500
    assert summary["prompt_tokens"] == 3000
    assert summary["candidate_tokens"] == 1500
    assert summary["agent_calls"]["watcher"] == 1
    assert summary["agent_calls"]["diagnostician"] == 1
    assert len(summary["recent_invocations"]) == 2

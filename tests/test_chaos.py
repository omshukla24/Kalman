"""Tests for Chaos Engineering & Resilience Engine."""
from kalman.chaos.engine import ChaosEngine


def test_chaos_launch_and_resilience_grading():
    injected_calls = []

    def mock_injector(sig, mult, secs, reg):
        injected_calls.append((sig, mult, secs, reg))

    chaos = ChaosEngine(injector_hook=mock_injector)
    exp = chaos.launch_experiment("cdn_flapping", duration_s=5.0)

    assert exp.name == "cdn_flapping"
    assert exp.status == "ACTIVE"
    assert len(injected_calls) == 1
    assert injected_calls[0][0] == "cdn_5xx_rate"

    # Simulate fast detection by Watcher in 3.2s
    chaos.record_detection("cdn_5xx_rate")
    assert exp.detected is True
    assert exp.detection_latency_s is not None
    assert exp.detection_latency_s >= 0.0

    # Complete experiment and verify elite A+ grade
    completed = chaos.complete_experiment(exp.experiment_id, mttr_seconds=12.0)
    assert completed is not None
    assert completed.status == "COMPLETED"
    assert "A+" in completed.resilience_grade

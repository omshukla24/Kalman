"""Tests for Markov Chain Outage Projections, Failure Forensics, OTel, and Circuit Breakers."""
from kalman.ml.failure_forensics import FailureForensicsEngine
from kalman.ml.markov_chain import BroadcastMarkovChain
from kalman.security.circuit_breaker import CircuitBreaker
from kalman.security.cvaa_compliance import CVAAComplianceMonitor
from kalman.telemetry.opentelemetry_exporter import OpenTelemetryExporter


def test_markov_chain_state_projections():
    chain = BroadcastMarkovChain()
    # Nominal z-score
    nominal_proj = chain.project_state(current_z=1.0)
    assert nominal_proj.current_state == "OPTIMAL"
    assert nominal_proj.p_optimal_30s > 50.0

    # High z-score (crisis)
    crisis_proj = chain.project_state(current_z=12.0)
    assert crisis_proj.current_state == "BUFFERING_CRISIS"
    assert crisis_proj.p_buffering_crisis_30s > 0.0


def test_failure_forensics_super_bowl_match():
    engine = FailureForensicsEngine()
    # Recreate signature resembling Super Bowl CDN collapse
    snapshot = {
        "rebuffer_ratio": 0.075,
        "cdn_5xx_rate": 50.0,
        "encoder_health": 0.95,
        "startup_latency_ms": 4000.0,
        "packet_loss_pct": 0.4,
    }
    match = engine.match_signature(snapshot)
    assert match is not None
    assert "Super Bowl" in match.disaster_name
    assert match.similarity_score_pct >= 70.0


def test_otel_exporter_w3c_traces():
    exporter = OpenTelemetryExporter()
    trace_id = exporter.start_trace()
    assert len(trace_id) == 32

    span1 = exporter.record_span(
        trace_id=trace_id,
        name="Watcher.tick",
        start_time_s=100.0,
        end_time_s=100.05,
        attributes={"status": "ok"},
    )
    span2 = exporter.record_span(
        trace_id=trace_id,
        name="Diagnostician.diagnose",
        start_time_s=100.06,
        end_time_s=100.45,
        parent_span_id=span1.span_id,
    )

    assert span1.duration_ms == 50.0
    assert span2.parent_span_id == span1.span_id
    summary = exporter.get_traces_summary()
    assert len(summary) >= 2
    assert summary[-1]["w3c_header"].startswith("00-")


def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker("test_api", failure_threshold=3, recovery_timeout_s=0.1)
    assert cb.can_execute() is True
    assert cb.state == "CLOSED"

    # Trip the breaker
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == "OPEN"
    assert cb.can_execute() is False

    # Simulate timeout
    import time
    time.sleep(0.12)
    assert cb.can_execute() is True
    assert cb.state == "HALF_OPEN"

    # Two consecutive successes recover the circuit
    cb.record_success()
    cb.record_success()
    assert cb.state == "CLOSED"


def test_cvaa_caption_compliance():
    monitor = CVAAComplianceMonitor()
    pass_report = monitor.check_captions(fault_factor=1.0)
    assert pass_report.status == "PASS"
    assert pass_report.is_fcc_compliant is True
    assert pass_report.dropped_cues_count == 0

    fail_report = monitor.check_captions(fault_factor=3.0)
    assert fail_report.status == "VIOLATION"
    assert fail_report.is_fcc_compliant is False
    assert fail_report.dropped_cues_count > 0

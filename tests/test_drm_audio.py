"""Tests for Multi-DRM License Health and EBU R128 Audio Loudness Compliance."""
from kalman.broadcast.audio_compliance import AudioComplianceMonitor
from kalman.broadcast.drm_server import DRMServerMonitor


def test_drm_health_nominal():
    monitor = DRMServerMonitor()
    reports = monitor.check_drm_health(fault_factor=1.0)

    assert "widevine" in reports
    assert "fairplay" in reports
    assert "playready" in reports

    for name, r in reports.items():
        assert r.health_status in ("OPTIMAL", "SLOW")
        assert r.success_rate_pct >= 99.0
        assert r.latency_ms < 150.0


def test_drm_health_degraded():
    monitor = DRMServerMonitor()
    reports = monitor.check_drm_health(fault_factor=5.5)

    assert any(r.health_status == "DEGRADED" for r in reports.values())
    assert any(r.latency_ms > 200.0 for r in reports.values())


def test_audio_compliance_nominal():
    monitor = AudioComplianceMonitor()
    report = monitor.evaluate_audio(fault_factor=1.0)

    assert report.is_compliant is True
    assert report.status == "COMPLIANT"
    assert -25.5 <= report.integrated_lufs <= -22.5
    assert report.true_peak_dbfs <= -1.0


def test_audio_compliance_loudness_spike():
    monitor = AudioComplianceMonitor()
    report = monitor.evaluate_audio(fault_factor=3.0)

    assert report.is_compliant is False
    assert report.status in ("WARNING", "NON_COMPLIANT")
    assert report.integrated_lufs > -23.0
    assert report.violation_reason is not None

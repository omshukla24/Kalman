"""Tests for Incident Notifier & Webhook Dispatcher."""
from kalman.agents.notifier import Notifier


def test_notifier_dispatch_incident_alert():
    notif = Notifier()
    evidence = [
        {"claim": "cdn_5xx_rate surged to 54/s", "query_id": "q-1"},
        {"claim": "502 Gateway errors in logs", "query_id": "q-2"},
    ]

    alert = notif.dispatch_incident_alert(
        incident_id="inc-502-01",
        severity="P1_CRITICAL",
        signal="eu-west:cdn_5xx_rate",
        root_cause="Edge proxy timeout cascade",
        evidence=evidence,
        action="shift_cdn_traffic",
    )

    assert alert.incident_id == "inc-502-01"
    assert alert.severity == "P1_CRITICAL"
    assert "blocks" in alert.payload["attachments"][0]
    assert len(notif.dispatch_log) == 1


def test_notifier_dispatch_recovery_alert():
    notif = Notifier()
    rec_alert = notif.dispatch_recovery_alert("inc-502-01", "eu-west:cdn_5xx_rate", mttr_seconds=12.4)

    assert rec_alert.severity == "RECOVERED"
    assert "12.4s" in rec_alert.summary
    assert len(notif.dispatch_log) == 1

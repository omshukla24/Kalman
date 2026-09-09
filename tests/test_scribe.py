"""Tests for Scribe narrative synthesis and grounding proof."""
from kalman.agents.scribe import Scribe, grounded


def test_scribe_compose_grounded_postmortem():
    scribe = Scribe()
    evidence = [
        {"claim": "cdn_5xx_rate surged to 54.2 req/s", "query_id": "q-1"},
        {"claim": "502 Bad Gateway observed in edge logs", "query_id": "q-2"},
    ]
    executed_queries = {"q-1", "q-2", "q-3"}

    pm = scribe.compose_postmortem(
        incident_id="inc-cdn-1001",
        root_cause="Edge CDN gateway timeout cascade",
        evidence_list=evidence,
        executed_query_ids=executed_queries,
        remediation_action="shift_cdn_traffic",
        mttr_seconds=14.5,
    )

    assert pm.incident_id == "inc-cdn-1001"
    assert pm.integrity_score == 1.0
    assert grounded(pm, executed_queries) is True
    assert len(pm.claims) == 2
    assert all(c.verified for c in pm.claims)

    md = pm.to_markdown()
    assert "inc-cdn-1001" in md
    assert "14.5s" in md
    assert "Verified (Proof on Record)" in md


def test_scribe_flags_unverified_claims():
    scribe = Scribe()
    evidence = [
        {"claim": "cdn_5xx_rate surged to 54.2 req/s", "query_id": "q-1"},
        {"claim": "a hallucinated number with fake query", "query_id": "q-fake"},
    ]
    executed_queries = {"q-1"}

    pm = scribe.compose_postmortem(
        incident_id="inc-test-2",
        root_cause="Test",
        evidence_list=evidence,
        executed_query_ids=executed_queries,
    )

    assert pm.integrity_score == 0.5
    assert "[UNVERIFIED]" in pm.claims[1].text
    assert pm.claims[1].verified is False
    assert grounded(pm, executed_queries) is False

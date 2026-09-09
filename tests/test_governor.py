"""The Governor must enforce the allowlist, bounds, and human gates."""
from kalman.agents.governor import Governor


def _gov():
    return Governor(
        policy={
            "allowed_actions": {
                "shift_cdn_traffic": {"max": {"pct": 25}, "requires_human": False},
                "failover_to_backup_stream": {"requires_human": True},
            }
        }
    )


def test_blocks_unknown_action():
    assert _gov().review("delete_everything", {}).approved is False


def test_blocks_out_of_bounds():
    assert _gov().review("shift_cdn_traffic", {"pct": 80}).approved is False


def test_allows_within_bounds():
    assert _gov().review("shift_cdn_traffic", {"pct": 10}).approved is True


def test_destructive_requires_human():
    d = _gov().review("failover_to_backup_stream", {})
    assert d.approved is False and d.requires_human is True


def test_audit_log_records_every_decision():
    g = _gov()
    g.review("shift_cdn_traffic", {"pct": 10})
    g.review("delete_everything", {})
    assert len(g.audit_log) == 2

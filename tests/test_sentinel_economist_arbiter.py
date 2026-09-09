"""Tests for Sentinel Security Agent, Financial Economist, and Consensus Arbiter."""
from kalman.agents.arbiter import AgentProposal, ConsensusArbiter
from kalman.agents.economist import EconomistAgent
from kalman.agents.sentinel import SentinelAgent


def test_sentinel_origin_flood_detection():
    sentinel = SentinelAgent()
    nominal = sentinel.inspect_traffic(fault_factor=1.0)
    assert nominal.threat_level == "GREEN"
    assert nominal.attack_signature is None

    attack = sentinel.inspect_traffic(fault_factor=3.5)
    assert attack.threat_level == "ATTACK_ACTIVE"
    assert attack.attack_signature is not None
    assert attack.blocked_ips_count > 0


def test_economist_blast_radius_calculation():
    economist = EconomistAgent(cpm=35.0, arpu_monthly=15.0)

    # Pristine broadcast
    nominal = economist.calculate_tick_impact(
        concurrent_viewers=100000,
        rebuffer_ratio=0.002,
        cdn_5xx_rate=0.5,
    )
    assert nominal.business_impact_level == "NEGLIGIBLE"

    # Severe buffering event
    severe = economist.calculate_tick_impact(
        concurrent_viewers=500000,
        rebuffer_ratio=0.15,
        cdn_5xx_rate=80.0,
    )
    assert severe.business_impact_level in ("CRITICAL", "SEVERE")
    assert severe.ad_impression_loss_usd > 0.0
    assert severe.sla_penalty_exposure_usd > 0.0


def test_arbiter_resolves_consensus_within_governor_bounds():
    arbiter = ConsensusArbiter()
    governor_allowlist = {
        "shift_cdn_traffic": {"max": {"pct": 30.0}},
        "throttle_bitrate_ladder": {"max": {"max_kbps": 4000.0}},
    }

    proposals = [
        AgentProposal(
            agent="Diagnostician",
            action="shift_cdn_traffic",
            params={"pct": 20.0},
            priority=8,
            justification="Mitigate 5xx spike",
        ),
        AgentProposal(
            agent="Economist",
            action="shift_cdn_traffic",
            params={"pct": 10.0},
            priority=6,
            justification="Cost conservation",
        ),
    ]

    consensus = arbiter.arbitrate(proposals, governor_allowlist)
    assert consensus.selected_action == "shift_cdn_traffic"
    assert consensus.effective_params["pct"] == 20.0
    assert "Diagnostician" in consensus.supporting_agents
    assert consensus.consensus_score_pct == 100.0

"""Arbiter — Multi-Agent Consensus & Policy Resolution Engine.

Resolves conflicting recommendations from multiple specialized agents:
  - Diagnostician (optimizes for technical recovery)
  - Economist (optimizes for financial preservation & egress budget)
  - Sentinel (optimizes for perimeter defense)
  - Governor (enforces hard compliance boundaries)

Generates a unified, consensus-backed remediation plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentProposal:
    agent: str
    action: str
    params: dict
    priority: int       # 1 (lowest) to 10 (highest)
    justification: str


@dataclass
class ArbitratedConsensus:
    selected_action: str
    effective_params: dict
    consensus_score_pct: float
    supporting_agents: list[str]
    dissenting_agents: list[str]
    arbitration_rationale: str


class ConsensusArbiter:
    def arbitrate(
        self,
        proposals: list[AgentProposal],
        governor_allowlist: dict,
    ) -> ArbitratedConsensus:
        if not proposals:
            return ArbitratedConsensus(
                selected_action="none",
                effective_params={},
                consensus_score_pct=100.0,
                supporting_agents=[],
                dissenting_agents=[],
                arbitration_rationale="No proposals submitted.",
            )

        # 1. Filter out proposals that violate hard governor allowlist
        valid_proposals = []
        for p in proposals:
            if p.action in governor_allowlist:
                spec = governor_allowlist[p.action]
                bounds = spec.get("max", {})
                # Check numeric caps
                violated = any(float(p.params.get(k, 0)) > float(cap) for k, cap in bounds.items())
                if not violated:
                    valid_proposals.append(p)

        if not valid_proposals:
            # Clamp the highest priority proposal to governor bounds
            fallback = max(proposals, key=lambda x: x.priority)
            clamped_params = dict(fallback.params)
            spec = governor_allowlist.get(fallback.action, {})
            for k, cap in spec.get("max", {}).items():
                if k in clamped_params:
                    clamped_params[k] = min(clamped_params[k], cap)

            return ArbitratedConsensus(
                selected_action=fallback.action,
                effective_params=clamped_params,
                consensus_score_pct=60.0,
                supporting_agents=[fallback.agent],
                dissenting_agents=["Governor"],
                arbitration_rationale=f"Clamped {fallback.action} parameters to comply with policy bounds.",
            )

        # 2. Select proposal with highest priority score
        winner = max(valid_proposals, key=lambda x: x.priority)
        supporters = [p.agent for p in valid_proposals if p.action == winner.action]
        dissenters = [p.agent for p in proposals if p.action != winner.action]

        score = (len(supporters) / max(1, len(proposals))) * 100.0

        return ArbitratedConsensus(
            selected_action=winner.action,
            effective_params=winner.params,
            consensus_score_pct=round(score, 1),
            supporting_agents=supporters,
            dissenting_agents=dissenters,
            arbitration_rationale=f"Selected {winner.action} supported by {', '.join(supporters)}: {winner.justification}",
        )


arbiter = ConsensusArbiter()

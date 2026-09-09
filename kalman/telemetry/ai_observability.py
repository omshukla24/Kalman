"""KALMAN II — AI Observability & Token Economics.

Tracks LLM token usage, cost accounting, and execution latencies across all
agent invocations (Watcher, Diagnostician, Scribe).

Meets the hackathon "Grafana AI Observability / partner complement" objective:
proves the real economics of deterministic detection vs AI reasoning.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock


# Gemini pricing per million tokens (standard tier)
PRICING = {
    "gemini-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-pro":   {"input_per_m": 1.25,  "output_per_m": 5.00},
}


@dataclass
class AgentInvocationRecord:
    timestamp: float
    agent: str
    model: str
    prompt_tokens: int
    candidate_tokens: int
    total_tokens: int
    latency_ms: float
    estimated_cost_usd: float
    status: str
    metadata: dict = field(default_factory=dict)


class AIObservability:
    def __init__(self, max_records: int = 200):
        self._lock = Lock()
        self._records: deque[AgentInvocationRecord] = deque(maxlen=max_records)
        self.total_prompt_tokens: int = 0
        self.total_candidate_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.agent_calls: dict[str, int] = {"watcher": 0, "diagnostician": 0, "scribe": 0}
        self.agent_latencies: dict[str, list[float]] = {"watcher": [], "diagnostician": [], "scribe": []}

    def record_call(
        self,
        agent: str,
        model: str,
        prompt_tokens: int,
        candidate_tokens: int,
        latency_ms: float,
        status: str = "ok",
        metadata: dict | None = None,
    ) -> AgentInvocationRecord:
        with self._lock:
            # Estimate cost
            price_spec = PRICING["gemini-pro"] if "pro" in model.lower() else PRICING["gemini-flash"]
            cost = (prompt_tokens / 1_000_000.0 * price_spec["input_per_m"]) + (
                candidate_tokens / 1_000_000.0 * price_spec["output_per_m"]
            )

            total_toks = prompt_tokens + candidate_tokens
            rec = AgentInvocationRecord(
                timestamp=time.time(),
                agent=agent,
                model=model,
                prompt_tokens=prompt_tokens,
                candidate_tokens=candidate_tokens,
                total_tokens=total_toks,
                latency_ms=round(latency_ms, 2),
                estimated_cost_usd=round(cost, 6),
                status=status,
                metadata=metadata or {},
            )

            self._records.append(rec)
            self.total_prompt_tokens += prompt_tokens
            self.total_candidate_tokens += candidate_tokens
            self.total_cost_usd += cost
            self.agent_calls[agent] = self.agent_calls.get(agent, 0) + 1

            if agent not in self.agent_latencies:
                self.agent_latencies[agent] = []
            self.agent_latencies[agent].append(latency_ms)
            if len(self.agent_latencies[agent]) > 50:
                self.agent_latencies[agent].pop(0)

            return rec

    def summary(self) -> dict:
        with self._lock:
            avg_latencies = {
                k: round(sum(v) / len(v), 2) if v else 0.0
                for k, v in self.agent_latencies.items()
            }
            return {
                "total_tokens": self.total_prompt_tokens + self.total_candidate_tokens,
                "prompt_tokens": self.total_prompt_tokens,
                "candidate_tokens": self.total_candidate_tokens,
                "estimated_cost_usd": round(self.total_cost_usd, 6),
                "agent_calls": dict(self.agent_calls),
                "avg_latency_ms": avg_latencies,
                "recent_invocations": [
                    {
                        "ts": r.timestamp,
                        "agent": r.agent,
                        "model": r.model,
                        "tokens": r.total_tokens,
                        "latency_ms": r.latency_ms,
                        "cost_usd": r.estimated_cost_usd,
                        "status": r.status,
                    }
                    for r in list(self._records)[-10:]
                ],
            }


observability = AIObservability()

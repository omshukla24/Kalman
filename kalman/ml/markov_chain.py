"""Discrete-Time Markov Chain (DTMC) for Broadcast Outage Probability Modeling.

Models the dynamic broadcast stream state transitions:
    S0: OPTIMAL_BROADCAST
    S1: ELEVATED_JITTER
    S2: BUFFERING_CRISIS
    S3: AUTONOMOUS_HEALING

Projects multi-step forward transition probabilities:
    P(Blackout within t=60s) = P^k[0, 2]
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarkovProjection:
    current_state: str
    p_optimal_30s: float
    p_buffering_crisis_30s: float
    p_buffering_crisis_60s: float
    system_entropy: float


class BroadcastMarkovChain:
    def __init__(self):
        self.states = ["OPTIMAL", "ELEVATED_JITTER", "BUFFERING_CRISIS", "AUTONOMOUS_HEALING"]
        # Nominal transition matrix (1-tick transitions)
        self.P = [
            [0.96, 0.03, 0.005, 0.005],  # from OPTIMAL
            [0.20, 0.65, 0.12,  0.03],   # from ELEVATED_JITTER
            [0.01, 0.04, 0.80,  0.15],   # from BUFFERING_CRISIS
            [0.60, 0.15, 0.05,  0.20],   # from AUTONOMOUS_HEALING
        ]

    def _matrix_mult(self, A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
        n = len(A)
        res = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                res[i][j] = sum(A[i][k] * B[k][j] for k in range(n))
        return res

    def project_state(self, current_z: float, steps: int = 30) -> MarkovProjection:
        # Determine initial state from current Kalman z-score
        if current_z > 8.0:
            state_idx = 2  # BUFFERING_CRISIS
        elif current_z > 4.0:
            state_idx = 1  # ELEVATED_JITTER
        else:
            state_idx = 0  # OPTIMAL

        # Compute P^30
        p_curr = [row[:] for row in self.P]
        for _ in range(steps - 1):
            p_curr = self._matrix_mult(p_curr, self.P)

        p_crisis_30 = p_curr[state_idx][2]

        # Compute P^60
        p_60 = self._matrix_mult(p_curr, p_curr)
        p_crisis_60 = p_60[state_idx][2]

        return MarkovProjection(
            current_state=self.states[state_idx],
            p_optimal_30s=round(p_curr[state_idx][0] * 100.0, 1),
            p_buffering_crisis_30s=round(p_crisis_30 * 100.0, 1),
            p_buffering_crisis_60s=round(p_crisis_60 * 100.0, 1),
            system_entropy=round(-sum(p * (0.0 if p <= 0 else (p - 1.0)) for p in p_curr[state_idx]), 3),
        )


markov_chain = BroadcastMarkovChain()

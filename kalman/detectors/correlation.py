"""Multi-Signal Cross-Correlation & Blast Radius Engine.

Computes rolling Pearson correlation coefficients across telemetry signals to:
  1. Determine whether simultaneous anomalies are coupled (e.g., origin failure vs network choke).
  2. Identify the root initiator (which signal deviated first in time).
  3. Map the topological blast radius across broadcast infrastructure.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class CorrelationPair:
    signal_a: str
    signal_b: str
    coefficient: float      # -1.0 to +1.0
    relationship: str       # COUPLED, INVERSE, INDEPENDENT


@dataclass
class BlastRadiusReport:
    initiator_signal: str
    coupled_signals: list[str]
    is_systemic: bool
    affected_audience_pct: float
    infrastructure_layer: str  # ORIGIN_TRANSCODER, CDN_EDGE, LAST_MILE_NETWORK
    correlation_matrix: dict[str, dict[str, float]]


class CorrelationEngine:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._history: dict[str, deque[float]] = {}
        self._first_spike_time: dict[str, float] = {}

    def observe(self, signal: str, value: float) -> None:
        if signal not in self._history:
            self._history[signal] = deque(maxlen=self.window_size)
        self._history[signal].append(float(value))

    def record_spike(self, signal: str) -> None:
        if signal not in self._first_spike_time:
            self._first_spike_time[signal] = time.time()

    def clear_spike(self, signal: str) -> None:
        self._first_spike_time.pop(signal, None)

    def compute_pearson(self, sig_a: str, sig_b: str) -> float:
        """Compute rolling Pearson correlation between two signals."""
        hist_a = list(self._history.get(sig_a, []))
        hist_b = list(self._history.get(sig_b, []))

        min_len = min(len(hist_a), len(hist_b))
        if min_len < 5:
            return 0.0

        x = hist_a[-min_len:]
        y = hist_b[-min_len:]

        mean_x = sum(x) / min_len
        mean_y = sum(y) / min_len

        dx = [val - mean_x for val in x]
        dy = [val - mean_y for val in y]

        sum_prod = sum(dx[i] * dy[i] for i in range(min_len))
        sum_sq_x = sum(val * val for val in dx)
        sum_sq_y = sum(val * val for val in dy)

        den = math.sqrt(sum_sq_x * sum_sq_y)
        if den < 1e-12:
            return 0.0

        r = sum_prod / den
        return round(max(-1.0, min(1.0, r)), 3)

    def analyze_incident(self, active_anomalies: list[dict]) -> BlastRadiusReport:
        """Derive root initiator and coupled signals from active anomalies."""
        signals = [a["signal"] for a in active_anomalies]
        if not signals:
            return BlastRadiusReport(
                initiator_signal="none",
                coupled_signals=[],
                is_systemic=False,
                affected_audience_pct=0.0,
                infrastructure_layer="NOMINAL",
                correlation_matrix={},
            )

        # Build pairwise correlation matrix
        matrix: dict[str, dict[str, float]] = {s: {} for s in signals}
        for s1 in signals:
            for s2 in signals:
                if s1 == s2:
                    matrix[s1][s2] = 1.0
                else:
                    matrix[s1][s2] = self.compute_pearson(s1, s2)

        # Identify initiator: signal with earliest first spike time
        initiator = min(
            signals,
            key=lambda s: self._first_spike_time.get(s, float("inf")),
        )

        coupled = [s for s in signals if s != initiator and abs(matrix.get(initiator, {}).get(s, 0.0)) >= 0.5]
        is_systemic = len(signals) >= 2 or "rebuffer" in initiator

        # Identify infrastructure layer
        if "encoder" in initiator or "av_sync" in initiator:
            layer = "ORIGIN_TRANSCODER"
        elif "cdn_5xx" in initiator or "startup_latency" in initiator:
            layer = "CDN_EDGE"
        else:
            layer = "LAST_MILE_NETWORK"

        # Estimate audience impact
        if is_systemic:
            impact_pct = min(95.0, 35.0 + len(signals) * 20.0)
        else:
            impact_pct = 15.0

        return BlastRadiusReport(
            initiator_signal=initiator,
            coupled_signals=coupled,
            is_systemic=is_systemic,
            affected_audience_pct=round(impact_pct, 1),
            infrastructure_layer=layer,
            correlation_matrix=matrix,
        )


correlation_engine = CorrelationEngine()

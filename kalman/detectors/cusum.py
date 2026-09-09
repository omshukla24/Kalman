"""Cumulative Sum (CUSUM) Change-Point Detector.

Detects subtle, persistent parameter drifts and structural changes that do not
trigger single-sample 5-sigma outlier gates.

Formulation:
    S_k^+ = max(0, S_{k-1}^+ + (z_k - mu) - k)
    S_k^- = max(0, S_{k-1}^- - (z_k - mu) - k)
    Decision: Alarm when S_k^+ > h (positive drift) or S_k^- > h (negative drift)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CUSUMResult:
    signal: str
    value: float
    s_pos: float
    s_neg: float
    alarm: bool
    drift_direction: str  # POSITIVE, NEGATIVE, NONE


class CUSUMDetector:
    def __init__(self, slack: float = 0.5, threshold: float = 5.0):
        self.slack = slack              # allowance k
        self.threshold = threshold      # decision boundary h
        self._s_pos: dict[str, float] = {}
        self._s_neg: dict[str, float] = {}
        self._mean: dict[str, float] = {}
        self._count: dict[str, int] = {}

    def observe(self, signal: str, value: float) -> CUSUMResult:
        val = float(value)
        n = self._count[signal] = self._count.get(signal, 0) + 1

        # Online mean estimation
        if n == 1:
            self._mean[signal] = val
            self._s_pos[signal] = 0.0
            self._s_neg[signal] = 0.0
            return CUSUMResult(signal, val, 0.0, 0.0, False, "NONE")

        mu = self._mean[signal]
        # Gentle online update of mean (EWMA)
        self._mean[signal] = 0.98 * mu + 0.02 * val

        diff = val - mu
        s_pos = max(0.0, self._s_pos[signal] + diff - self.slack)
        s_neg = max(0.0, self._s_neg[signal] - diff - self.slack)

        self._s_pos[signal] = s_pos
        self._s_neg[signal] = s_neg

        alarm = (s_pos > self.threshold) or (s_neg > self.threshold)
        direction = "POSITIVE" if s_pos > self.threshold else ("NEGATIVE" if s_neg > self.threshold else "NONE")

        return CUSUMResult(
            signal=signal,
            value=val,
            s_pos=round(s_pos, 3),
            s_neg=round(s_neg, 3),
            alarm=alarm,
            drift_direction=direction,
        )

    def reset(self, signal: str) -> None:
        self._s_pos[signal] = 0.0
        self._s_neg[signal] = 0.0


cusum_detector = CUSUMDetector()

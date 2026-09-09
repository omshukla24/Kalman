"""Forecaster — predicts a breach before it happens (KALMAN II upgrade).

Uses the Kalman filter's estimate trajectory and rolling linear regression to
project future values across multiple horizons (15s, 30s, 60s) and compute
exact seconds-to-threshold.

Allows the crew to act pre-emptively (e.g., proactive CDN traffic shedding)
instead of reactively waiting for viewers to experience a buffer freeze.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class ForecastProjection:
    signal: str
    current_estimate: float
    slope_per_s: float
    threshold: float
    seconds_to_breach: float | None
    risk_score: float  # 0.0 (safe) to 100.0 (critical imminent breach)
    projections: dict[str, float]  # horizon -> projected value
    status: str  # NORMAL, WATCH, IMMINENT_BREACH
    message: str


class Forecaster:
    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        self._history: dict[str, deque] = {}  # signal -> deque of (time, estimate)

    def observe(self, signal: str, estimate: float, timestamp: float | None = None) -> None:
        """Record an estimate point for rolling trajectory estimation."""
        if signal not in self._history:
            self._history[signal] = deque(maxlen=self.window_size)
        ts = timestamp or time.time()
        self._history[signal].append((ts, float(estimate)))

    def compute_slope(self, signal: str) -> float:
        """Compute rate of change (estimate delta per second) via OLS regression."""
        pts = list(self._history.get(signal, []))
        if len(pts) < 3:
            return 0.0

        n = len(pts)
        t_base = pts[0][0]
        times = [t - t_base for t, _ in pts]
        vals = [v for _, v in pts]

        mean_t = sum(times) / n
        mean_v = sum(vals) / n

        num = sum((times[i] - mean_t) * (vals[i] - mean_v) for i in range(n))
        den = sum((times[i] - mean_t) ** 2 for i in range(n))

        if abs(den) < 1e-9:
            return 0.0
        return num / den

    def seconds_to_threshold(
        self,
        estimate: float,
        slope_per_s: float,
        threshold: float,
        is_lower_bound: bool = False,
    ) -> float | None:
        """Return seconds until `threshold` is crossed, or None if not heading there."""
        if is_lower_bound:
            # Dangerous if falling below threshold (e.g. encoder health)
            if slope_per_s >= 0 or estimate <= threshold:
                return None
            return (threshold - estimate) / slope_per_s
        else:
            # Dangerous if rising above threshold (e.g. rebuffer, 5xx rate)
            if slope_per_s <= 0 or estimate >= threshold:
                return None
            return (threshold - estimate) / slope_per_s

    def forecast_signal(
        self,
        signal: str,
        current_val: float,
        threshold: float,
        is_lower_bound: bool = False,
        timestamp: float | None = None,
    ) -> ForecastProjection:
        self.observe(signal, current_val, timestamp=timestamp)
        slope = self.compute_slope(signal)
        ttb = self.seconds_to_threshold(current_val, slope, threshold, is_lower_bound)

        # Projections at 15s, 30s, 60s
        proj_15s = current_val + slope * 15.0
        proj_30s = current_val + slope * 30.0
        proj_60s = current_val + slope * 60.0

        # Calculate risk score (0-100)
        risk = 0.0
        status = "NORMAL"
        msg = f"{signal} trajectory is stable (slope: {slope:+.3f}/s)."

        if ttb is not None:
            if ttb <= 30.0:
                risk = min(100.0, 70.0 + (30.0 - ttb))
                status = "IMMINENT_BREACH"
                msg = f"WARNING: {signal} will breach danger threshold ({threshold}) in ~{int(ttb)}s!"
            elif ttb <= 90.0:
                risk = min(70.0, 30.0 + (90.0 - ttb) * 0.6)
                status = "WATCH"
                msg = f"WATCH: {signal} trending toward threshold ({threshold}) in ~{int(ttb)}s."
        elif (not is_lower_bound and current_val >= threshold) or (is_lower_bound and current_val <= threshold):
            risk = 100.0
            status = "BREACHED"
            msg = f"CRITICAL: {signal} is currently violating threshold ({current_val:.3f} vs {threshold})!"

        return ForecastProjection(
            signal=signal,
            current_estimate=round(current_val, 4),
            slope_per_s=round(slope, 5),
            threshold=threshold,
            seconds_to_breach=round(ttb, 1) if ttb is not None else None,
            risk_score=round(risk, 1),
            projections={
                "15s": round(proj_15s, 4),
                "30s": round(proj_30s, 4),
                "60s": round(proj_60s, 4),
            },
            status=status,
            message=msg,
        )

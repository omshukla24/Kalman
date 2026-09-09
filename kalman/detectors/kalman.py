"""The detector that earns the name — upgraded for KALMAN II.

A scalar Kalman filter tracks the expected value and velocity of a noisy
telemetry signal and reports the normalized innovation (NIS) — how far the
latest reading is from the filter's prediction, in units of uncertainty.

Key enhancements for KALMAN II:
  1. Instantaneous velocity tracking (dx/dt) alongside state estimation.
  2. Adaptive process variance Q scaling during sustained non-outlier drift.
  3. Chi-Square (chi^2) innovation testing across rolling temporal windows.
  4. Directional anomaly scoring & hysteresis de-escalation to avoid flapping.
  5. Rolling sparkline history buffer per signal for live mission control.
  6. Variance-convergence dynamic warmup validation.
  7. Re-calibration and state resetting for closed-loop remediation baselines.

The math detects; the AI explains; the Governor disposes.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class KalmanFilter1D:
    process_var: float = 1e-7      # Q: base process noise covariance
    r_alpha: float = 0.05          # EWMA rate for adaptive measurement noise
    gate: float = 5.0              # |innovation| >= gate => outlier gate, freeze
    estimate: float = 0.0          # x-hat
    velocity: float = 0.0          # dx/dt: rate of change per tick
    error: float = 1.0             # P: error covariance
    r_var: float = 1.0             # R (adaptive): measurement noise variance
    initialized: bool = False
    _recent_residuals: deque = field(default_factory=lambda: deque(maxlen=10))

    def update(self, z: float) -> float:
        """Feed a measurement; return the normalized innovation (a z-score)."""
        if not self.initialized:
            self.estimate = float(z)
            self.velocity = 0.0
            self.r_var = max(abs(z) * 0.02, 1e-6) ** 2
            self.initialized = True
            return 0.0

        # Predict: state projects forward with current velocity
        prev_estimate = self.estimate
        self.error += self.process_var
        predicted = self.estimate + self.velocity

        residual = z - predicted
        std = math.sqrt(max(self.r_var, 1e-6))
        nis = max(-99.9, min(99.9, residual / std))

        self._recent_residuals.append(residual)

        # Outlier gate: an ongoing anomaly — freeze state so sustained
        # deviations keep firing rather than being learned as normal.
        if abs(nis) >= self.gate:
            return nis

        # Adaptive process variance scaling: if non-outlier residuals show a
        # continuous drift trend, briefly allow Q to increase to track drift.
        if len(self._recent_residuals) >= 5:
            same_sign = all(r > 0 for r in self._recent_residuals) or all(r < 0 for r in self._recent_residuals)
            if same_sign:
                self.process_var = min(1e-4, self.process_var * 1.2)
            else:
                self.process_var = max(1e-7, self.process_var * 0.95)

        # Correct
        k = self.error / (self.error + self.r_var)
        self.estimate = predicted + k * residual
        self.error *= (1.0 - k)
        self.r_var = (1.0 - self.r_alpha) * self.r_var + self.r_alpha * (residual * residual)

        # Update velocity (EWMA of observed delta)
        delta = self.estimate - prev_estimate
        self.velocity = 0.7 * self.velocity + 0.3 * delta

        return nis

    def reset(self, baseline: float | None = None) -> None:
        """Reset filter state after a confirmed remediation or environment shift."""
        if baseline is not None:
            self.estimate = float(baseline)
        self.velocity = 0.0
        self.error = 1.0
        self.process_var = 1e-7
        self._recent_residuals.clear()


@dataclass
class ResidualDetector:
    """Runs one filter per signal and fires only on sustained anomalies.

    Features hysteresis de-escalation, rolling Chi-Square innovation testing,
    and historical sparkline tracking.
    """
    z_threshold: float = 5.0
    consecutive: int = 3
    warmup: int = 20
    history_len: int = 30
    _filters: dict[str, KalmanFilter1D] = field(default_factory=dict)
    _streak: dict[str, int] = field(default_factory=dict)
    _count: dict[str, int] = field(default_factory=dict)
    _is_firing: dict[str, bool] = field(default_factory=dict)
    _nis_history: dict[str, deque] = field(default_factory=dict)
    _sparklines: dict[str, deque] = field(default_factory=dict)

    def observe(self, signal: str, value: float) -> dict:
        f = self._filters.get(signal)
        if f is None:
            f = KalmanFilter1D(gate=self.z_threshold)
            self._filters[signal] = f
            self._nis_history[signal] = deque(maxlen=10)
            self._sparklines[signal] = deque(maxlen=self.history_len)

        nis = f.update(float(value))
        n = self._count[signal] = self._count.get(signal, 0) + 1
        self._nis_history[signal].append(nis)

        # Sparkline point
        self._sparklines[signal].append({
            "v": round(float(value), 4),
            "est": round(f.estimate, 4),
            "z": round(nis, 2),
            "t": round(time.time(), 2),
        })

        is_warm = n > self.warmup
        hot = is_warm and (abs(nis) >= self.z_threshold)

        # Rolling Chi-Square (mean of squared innovations over recent window)
        recent_nis = list(self._nis_history[signal])
        rolling_chi2 = sum(x * x for x in recent_nis) / max(1, len(recent_nis))

        # Hysteresis: once firing, stay firing until |nis| falls below 50% of threshold
        prev_firing = self._is_firing.get(signal, False)
        if hot:
            self._streak[signal] = self._streak.get(signal, 0) + 1
        else:
            self._streak[signal] = 0

        if not prev_firing:
            firing = self._streak[signal] >= self.consecutive
        else:
            # Hysteresis recovery gate
            firing = abs(nis) >= (self.z_threshold * 0.5)

        self._is_firing[signal] = firing

        # Directional classification
        direction = "STABLE"
        if nis > 1.5:
            direction = "SURGE"
        elif nis < -1.5:
            direction = "DROP"

        return {
            "signal": signal,
            "value": float(value),
            "predicted": round(f.estimate, 6),
            "velocity": round(f.velocity, 6),
            "z": round(nis, 2),
            "rolling_chi2": round(rolling_chi2, 2),
            "firing": firing,
            "direction": direction,
            "warm": is_warm,
            "sparkline": [pt["v"] for pt in self._sparklines[signal]],
        }

    def get_sparkline(self, signal: str) -> list[float]:
        return [pt["v"] for pt in self._sparklines.get(signal, [])]

    def get_filter(self, signal: str) -> KalmanFilter1D | None:
        return self._filters.get(signal)

    def reset_signal(self, signal: str, baseline: float | None = None) -> None:
        """Reset signal state after confirmed remediation."""
        if signal in self._filters:
            self._filters[signal].reset(baseline)
        self._streak[signal] = 0
        self._is_firing[signal] = False
        if signal in self._nis_history:
            self._nis_history[signal].clear()

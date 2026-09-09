"""Multi-State Extended Kalman Filter (EKF) for Coupled Video Telemetry.

Tracks a 2-dimensional coupled state vector:
    x = [ position (telemetry value), velocity (instantaneous rate of change) ]^T

Formulation:
    Prediction:
        x_{k|k-1} = F * x_{k-1|k-1}
        P_{k|k-1} = F * P_{k-1|k-1} * F^T + Q
    Update:
        y_k = z_k - H * x_{k|k-1}  (residual)
        S_k = H * P_{k|k-1} * H^T + R  (innovation covariance)
        K_k = P_{k|k-1} * H^T * S_k^{-1}  (Kalman gain)
        x_{k|k} = x_{k|k-1} + K_k * y_k
        P_{k|k} = (I - K_k * H) * P_{k|k-1}
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class EKFState:
    estimate: float
    velocity: float
    covariance: list[list[float]]
    innovation: float
    nis_z: float
    is_outlier: bool


class ExtendedKalmanFilter2D:
    def __init__(
        self,
        dt: float = 1.0,
        q_pos: float = 1e-4,
        q_vel: float = 1e-3,
        r_var: float = 0.05,
        gate: float = 4.5,
    ):
        self.dt = dt
        self.gate = gate
        # State vector [x, dx/dt]
        self.x = [0.0, 0.0]
        # State covariance matrix P (2x2)
        self.P = [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
        # Process noise covariance Q (2x2)
        self.Q = [
            [q_pos * (dt**3) / 3.0, q_pos * (dt**2) / 2.0],
            [q_pos * (dt**2) / 2.0, q_vel * dt],
        ]
        # Measurement noise variance R
        self.R = r_var
        self.initialized: bool = False

    def update(self, z: float) -> EKFState:
        z = float(z)
        if not self.initialized:
            self.x = [z, 0.0]
            self.initialized = True
            return EKFState(
                estimate=z,
                velocity=0.0,
                covariance=[row[:] for row in self.P],
                innovation=0.0,
                nis_z=0.0,
                is_outlier=False,
            )

        dt = self.dt

        # 1. Predict: x_pred = F * x
        x_pred = [
            self.x[0] + self.x[1] * dt,
            self.x[1],
        ]

        # P_pred = F * P * F^T + Q
        # F = [[1, dt], [0, 1]]
        p00 = self.P[0][0] + dt * (self.P[1][0] + self.P[0][1]) + (dt**2) * self.P[1][1] + self.Q[0][0]
        p01 = self.P[0][1] + dt * self.P[1][1] + self.Q[0][1]
        p10 = self.P[1][0] + dt * self.P[1][1] + self.Q[1][0]
        p11 = self.P[1][1] + self.Q[1][1]
        P_pred = [[p00, p01], [p10, p11]]

        # 2. Innovation: y = z - H * x_pred (where H = [1, 0])
        y = z - x_pred[0]
        S = P_pred[0][0] + self.R
        std_innov = math.sqrt(max(1e-12, S))
        nis = y / std_innov

        is_outlier = abs(nis) >= self.gate
        if is_outlier:
            # Outlier gating: freeze state to prevent tracking spike
            return EKFState(
                estimate=round(self.x[0], 5),
                velocity=round(self.x[1], 5),
                covariance=[row[:] for row in self.P],
                innovation=round(y, 4),
                nis_z=round(nis, 2),
                is_outlier=True,
            )

        # 3. Kalman Gain: K = P_pred * H^T / S
        k0 = P_pred[0][0] / S
        k1 = P_pred[1][0] / S

        # 4. Correct: x = x_pred + K * y
        self.x[0] = x_pred[0] + k0 * y
        self.x[1] = x_pred[1] + k1 * y

        # 5. Update covariance: P = (I - K*H) * P_pred
        self.P[0][0] = (1.0 - k0) * P_pred[0][0]
        self.P[0][1] = (1.0 - k0) * P_pred[0][1]
        self.P[1][0] = P_pred[1][0] - k1 * P_pred[0][0]
        self.P[1][1] = P_pred[1][1] - k1 * P_pred[0][1]

        return EKFState(
            estimate=round(self.x[0], 5),
            velocity=round(self.x[1], 5),
            covariance=[row[:] for row in self.P],
            innovation=round(y, 4),
            nis_z=round(nis, 2),
            is_outlier=False,
        )

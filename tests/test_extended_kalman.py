"""Tests for 2D Coupled State-Space Extended Kalman Filter."""
from kalman.detectors.extended_kalman import ExtendedKalmanFilter2D


def test_ekf_initialization_and_first_step():
    ekf = ExtendedKalmanFilter2D(dt=1.0)
    state = ekf.update(10.0)

    assert state.estimate == 10.0
    assert state.velocity == 0.0
    assert state.is_outlier is False


def test_ekf_tracks_linear_ramp():
    ekf = ExtendedKalmanFilter2D(dt=1.0, q_pos=1e-3, q_vel=1e-2, r_var=0.01)

    # Feed a constant velocity ramp: 10, 12, 14, 16, 18, 20... (slope = 2.0)
    for t in range(15):
        val = 10.0 + 2.0 * t
        state = ekf.update(val)

    # Velocity estimate should converge close to 2.0
    assert abs(state.velocity - 2.0) < 0.5
    # Estimate should be close to 38.0
    assert abs(state.estimate - 38.0) < 1.0


def test_ekf_outlier_gating():
    ekf = ExtendedKalmanFilter2D(dt=1.0, gate=4.0, r_var=0.04)

    # Warm up at 10.0
    for _ in range(10):
        ekf.update(10.0)

    # Sudden 10x spike (e.g. single bitflip artifact)
    spike_state = ekf.update(100.0)
    assert spike_state.is_outlier is True
    # The filter estimate should remain protected at ~10.0
    assert abs(spike_state.estimate - 10.0) < 1.0

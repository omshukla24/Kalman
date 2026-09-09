"""Tests for CUSUM Change-Point Detector and Discrete Wavelet Denoiser."""
from kalman.detectors.cusum import CUSUMDetector
from kalman.detectors.wavelet import HaarWaveletFilter


def test_cusum_detects_sustained_drift():
    detector = CUSUMDetector(slack=0.2, threshold=3.0)

    # Establish baseline around 5.0
    for _ in range(15):
        res = detector.observe("test_signal", 5.0)
        assert res.alarm is False

    # Introduce subtle upward drift to 6.5
    alarm_fired = False
    for _ in range(10):
        res = detector.observe("test_signal", 6.5)
        if res.alarm:
            alarm_fired = True
            assert res.drift_direction == "POSITIVE"
            break

    assert alarm_fired is True


def test_wavelet_decomposition_and_denoise():
    wavelet = HaarWaveletFilter()
    raw_signal = [10.0, 10.2, 9.8, 10.1, 10.0, 10.3, 9.7, 10.1]

    decomp = wavelet.decompose_1d(raw_signal)
    assert len(decomp.approximation) == 4
    assert len(decomp.detail) == 4
    assert decomp.noise_variance >= 0.0

    denoised = wavelet.denoise(raw_signal)
    assert len(denoised) == len(raw_signal)

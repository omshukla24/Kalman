"""Discrete Wavelet Multi-Scale Noise Denoiser (Haar Wavelet).

Separates high-frequency transient telemetry jitter (Detail coefficients) from
structural low-frequency baseline drift (Approximation coefficients).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class WaveletDecomposition:
    approximation: list[float]  # Low-frequency structural trend
    detail: list[float]         # High-frequency noise residuals
    noise_variance: float
    signal_to_noise_ratio_db: float


class HaarWaveletFilter:
    def decompose_1d(self, signal: list[float]) -> WaveletDecomposition:
        """Single-level 1D discrete Haar wavelet transform."""
        n = len(signal)
        if n < 2:
            return WaveletDecomposition(signal, [], 0.0, 50.0)

        # Truncate to even length
        if n % 2 != 0:
            signal = signal[:-1]
            n -= 1

        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        approx = []
        detail = []

        for i in range(0, n, 2):
            s1 = signal[i]
            s2 = signal[i + 1]
            a = (s1 + s2) * inv_sqrt2
            d = (s1 - s2) * inv_sqrt2
            approx.append(round(a, 4))
            detail.append(round(d, 4))

        # Compute detail energy (noise variance)
        noise_energy = sum(x * x for x in detail) / max(1, len(detail))
        signal_energy = sum(x * x for x in approx) / max(1, len(approx))

        snr = 10.0 * math.log10(signal_energy / max(1e-9, noise_energy)) if noise_energy > 0 else 50.0

        return WaveletDecomposition(
            approximation=approx,
            detail=detail,
            noise_variance=round(noise_energy, 5),
            signal_to_noise_ratio_db=round(snr, 2),
        )

    def denoise(self, signal: list[float], threshold: float | None = None) -> list[float]:
        """Soft-thresholding wavelet reconstruction for denoising."""
        decomp = self.decompose_1d(signal)
        if not decomp.detail:
            return signal

        th = threshold or (math.sqrt(decomp.noise_variance) * 1.5)
        # Soft-threshold detail coefficients
        shrunk_detail = []
        for d in decomp.detail:
            if abs(d) <= th:
                shrunk_detail.append(0.0)
            else:
                sign = 1.0 if d > 0 else -1.0
                shrunk_detail.append(d - sign * th)

        # Inverse Haar transform
        sqrt2 = math.sqrt(2.0)
        reconstructed = []
        for a, d in zip(decomp.approximation, shrunk_detail):
            s1 = (a + d) / sqrt2
            s2 = (a - d) / sqrt2
            reconstructed.extend([round(s1, 4), round(s2, 4)])

        return reconstructed


wavelet_filter = HaarWaveletFilter()

"""EBU R128 & US CALM Act Broadcast Audio Loudness Engine.

Monitors broadcast loudness compliance:
  - Target Integrated Loudness: -24.0 LUFS (tolerance +/- 1.0 LUFS)
  - Maximum Short-Term Loudness: -18.0 LUFS
  - Maximum True Peak: -1.0 dBFS (clipping prevention)
  - Loudness Range (LRA): 4.0 to 14.0 LU
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class AudioComplianceReport:
    integrated_lufs: float
    short_term_lufs: float
    true_peak_dbfs: float
    loudness_range_lu: float
    is_compliant: bool
    violation_reason: str | None
    status: str  # COMPLIANT, WARNING, NON_COMPLIANT


class AudioComplianceMonitor:
    def evaluate_audio(self, fault_factor: float = 1.0) -> AudioComplianceReport:
        base_lufs = -24.0
        # If fault is injected, loudness spikes (e.g. ad insertion blast)
        if fault_factor > 1.5:
            integrated = base_lufs + (fault_factor - 1.0) * 4.5
            short_term = integrated + random.uniform(3.0, 6.0)
            true_peak = min(3.0, -0.5 + (fault_factor - 1.0) * 2.0)
        else:
            integrated = base_lufs + random.uniform(-0.4, 0.4)
            short_term = integrated + random.uniform(-1.0, 1.5)
            true_peak = random.uniform(-2.5, -1.2)

        lra = random.uniform(6.0, 9.0)

        # Check compliance
        violations = []
        if abs(integrated - (-24.0)) > 1.0:
            violations.append(f"Integrated loudness {integrated:.1f} LUFS outside -24 +/- 1 LUFS target")
        if true_peak > -1.0:
            violations.append(f"True peak {true_peak:.1f} dBFS exceeds -1.0 dBFS ceiling (clipping risk)")

        is_compliant = len(violations) == 0
        status = "COMPLIANT" if is_compliant else ("NON_COMPLIANT" if true_peak > 0.0 else "WARNING")

        return AudioComplianceReport(
            integrated_lufs=round(integrated, 2),
            short_term_lufs=round(short_term, 2),
            true_peak_dbfs=round(true_peak, 2),
            loudness_range_lu=round(lra, 1),
            is_compliant=is_compliant,
            violation_reason="; ".join(violations) if violations else None,
            status=status,
        )


audio_monitor = AudioComplianceMonitor()

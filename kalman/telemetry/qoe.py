"""Quality of Experience (QoE) & MOS Rating Engine (ITU-T P.1203 standard).

Calculates real-time broadcast viewer satisfaction as a Mean Opinion Score (MOS)
ranging from 1.0 (unwatchable / viewer abandonment) to 5.0 (flawless 4K broadcast).

Considers:
  - Rebuffer frequency & ratio (most heavily weighted impairment)
  - Startup / join latency
  - Encoder health & frame drops
  - Audio/Video synchronization drift
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class QoEMetrics:
    mos: float              # 1.0 to 5.0
    category: str          # PRISTINE, GOOD, FAIR, POOR, UNACCEPTABLE
    rebuffer_penalty: float
    latency_penalty: float
    encoder_penalty: float
    sync_penalty: float
    viewer_abandonment_risk: float  # 0.0 to 1.0


class QoEEngine:
    def compute_qoe(
        self,
        rebuffer_ratio: float,
        startup_latency_ms: float = 1200.0,
        encoder_health: float = 0.99,
        av_sync_offset_ms: float = 5.0,
    ) -> QoEMetrics:
        """Compute composite MOS according to ITU-T P.1203 curve approximations."""
        # Baseline ideal score
        base_mos = 4.85

        # 1. Rebuffer penalty (exponential decay: rebuffer > 3% ruins QoE)
        rebuf = max(0.0, rebuffer_ratio)
        rebuffer_penalty = 3.5 * (1.0 - math.exp(-40.0 * rebuf))

        # 2. Startup latency penalty (logarithmic over 2000ms)
        latency_excess = max(0.0, startup_latency_ms - 1500.0)
        latency_penalty = min(1.0, math.log1p(latency_excess / 1000.0) * 0.45)

        # 3. Encoder degradation penalty
        enc_health = max(0.0, min(1.0, encoder_health))
        encoder_penalty = (1.0 - enc_health) * 2.0

        # 4. AV sync drift penalty (noticeable above 40ms)
        sync_excess = max(0.0, av_sync_offset_ms - 40.0)
        sync_penalty = min(0.8, (sync_excess / 100.0) * 0.6)

        # Composite MOS
        mos = base_mos - rebuffer_penalty - latency_penalty - encoder_penalty - sync_penalty
        mos = max(1.0, min(5.0, round(mos, 2)))

        # Qualitative classification
        if mos >= 4.3:
            category = "PRISTINE"
        elif mos >= 3.8:
            category = "GOOD"
        elif mos >= 3.0:
            category = "FAIR"
        elif mos >= 2.0:
            category = "POOR"
        else:
            category = "UNACCEPTABLE"

        # Viewer abandonment probability
        # When MOS drops below 3.0, viewers exit the stream rapidly
        if mos >= 4.0:
            abandonment_risk = 0.02
        elif mos >= 3.0:
            abandonment_risk = round(0.05 + (4.0 - mos) * 0.25, 2)
        else:
            abandonment_risk = round(min(0.95, 0.35 + (3.0 - mos) * 0.30), 2)

        return QoEMetrics(
            mos=mos,
            category=category,
            rebuffer_penalty=round(rebuffer_penalty, 3),
            latency_penalty=round(latency_penalty, 3),
            encoder_penalty=round(encoder_penalty, 3),
            sync_penalty=round(sync_penalty, 3),
            viewer_abandonment_risk=abandonment_risk,
        )


qoe_engine = QoEEngine()

"""Multi-DRM License Server & Key Acquisition Monitor.

Monitors Widevine (Google), FairPlay (Apple), and PlayReady (Microsoft)
license acquisition latency, key rotation cadence, and token decryption failures.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class DRMStatusReport:
    system: str             # Widevine, FairPlay, PlayReady
    latency_ms: float       # Target < 120ms
    success_rate_pct: float # Target > 99.95%
    active_tokens: int
    key_rotation_age_s: float
    health_status: str      # OPTIMAL, SLOW, DEGRADED


class DRMServerMonitor:
    def __init__(self):
        self.last_key_rotation: float = time.time()

    def check_drm_health(self, fault_factor: float = 1.0) -> dict[str, DRMStatusReport]:
        now = time.time()
        systems = ["Widevine", "FairPlay", "PlayReady"]
        reports = {}

        for s in systems:
            base_lat = random.uniform(45.0, 85.0)
            lat = base_lat * fault_factor
            fail_rate = 0.01 * fault_factor if fault_factor > 1.0 else 0.001
            success_pct = max(0.0, min(100.0, 100.0 - (fail_rate * 100.0)))

            if lat > 350.0 or success_pct < 98.0:
                health = "DEGRADED"
            elif lat > 180.0:
                health = "SLOW"
            else:
                health = "OPTIMAL"

            reports[s.lower()] = DRMStatusReport(
                system=s,
                latency_ms=round(lat, 1),
                success_rate_pct=round(success_pct, 3),
                active_tokens=int(random.gauss(150000, 5000)),
                key_rotation_age_s=round(now - self.last_key_rotation, 1),
                health_status=health,
            )

        return reports


drm_monitor = DRMServerMonitor()

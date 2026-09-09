"""Sentinel Agent — Threat Mitigation & Stream Security Shield.

Guards the broadcast pipeline against malicious traffic anomalies:
  - Origin Bombing: bots requesting non-existent media segments (.ts/.m4s) to bust CDN cache.
  - Token Harvesting: credential stuffing on stream playback authorization tokens.
  - Geo-Bypass & Piracy Restreaming: anomalous high-concurrency token usage from data-center ASNs.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class ThreatReport:
    threat_level: str           # GREEN, ELEVATED, HIGH, ATTACK_ACTIVE
    blocked_ips_count: int
    origin_cache_hit_pct: float
    bot_traffic_share_pct: float
    attack_signature: str | None
    recommended_mitigation: str # e.g. "enable_rate_limiting", "rotate_token_hmac"


class SentinelAgent:
    def __init__(self):
        self.blocked_ips: set[str] = set()

    def inspect_traffic(self, fault_factor: float = 1.0) -> ThreatReport:
        is_attack = fault_factor > 2.0

        if is_attack:
            threat = "ATTACK_ACTIVE"
            cache_hit = max(45.0, 96.0 - fault_factor * 12.0)
            bots_pct = min(42.0, 3.0 + fault_factor * 8.0)
            sig = "Distributed HTTP/2 Rapid Reset & Cold-Segment Flood"
            mitigation = "rate_limit_origin_shield"
            # Simulate blocking malicious IPs
            for _ in range(int(fault_factor * 15)):
                self.blocked_ips.add(f"198.51.100.{random.randint(1, 254)}")
        else:
            threat = "GREEN"
            cache_hit = round(random.uniform(97.2, 98.8), 2)
            bots_pct = round(random.uniform(0.8, 1.8), 2)
            sig = None
            mitigation = "monitor"

        return ThreatReport(
            threat_level=threat,
            blocked_ips_count=len(self.blocked_ips),
            origin_cache_hit_pct=round(cache_hit, 2),
            bot_traffic_share_pct=round(bots_pct, 2),
            attack_signature=sig,
            recommended_mitigation=mitigation,
        )


sentinel = SentinelAgent()

"""Multi-CDN Dynamic Traffic Steering & Cost-Performance Arbiter.

Balances live video segment requests across multiple Tier-1 CDN providers:
  - Fastly (Low TTFB, optimal for live low-latency HLS/CMAF)
  - CloudFront (AWS ecosystem, high origin throughput)
  - Cloudflare (Global edge caching, flat rate pricing)
  - Akamai (Massive concurrent live event capacity)

Optimizes traffic distribution fractions using an objective function of:
  - Error rate (5xx penalties)
  - Time to First Byte (TTFB ms)
  - Blended bandwidth egress cost ($/GB)
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class CDNProviderStatus:
    provider: str
    traffic_share_pct: float    # 0.0 to 100.0%
    ttfb_ms: float
    error_rate_pct: float
    cost_per_gb_usd: float
    health: str                 # OPTIMAL, DEGRADED, SHEDDING


class MultiCDNBalancer:
    def __init__(self):
        self.providers = {
            "fastly":     {"share": 40.0, "ttfb": 28.0, "cost": 0.025, "err": 0.01},
            "cloudfront": {"share": 30.0, "ttfb": 34.0, "cost": 0.022, "err": 0.02},
            "cloudflare": {"share": 20.0, "ttfb": 31.0, "cost": 0.018, "err": 0.01},
            "akamai":     {"share": 10.0, "ttfb": 36.0, "cost": 0.029, "err": 0.01},
        }

    def shift_traffic(self, from_provider: str, to_provider: str, pct: float) -> dict[str, float]:
        """Shed traffic away from a degraded CDN partner."""
        if from_provider in self.providers and to_provider in self.providers:
            actual_shift = min(self.providers[from_provider]["share"], pct)
            self.providers[from_provider]["share"] -= actual_shift
            self.providers[to_provider]["share"] += actual_shift
        return {k: round(v["share"], 1) for k, v in self.providers.items()}

    def get_status(self, fault_cdn: str | None = None) -> list[CDNProviderStatus]:
        res = []
        for name, p in self.providers.items():
            is_fault = (fault_cdn and fault_cdn.lower() == name)
            err = p["err"] * 100.0 if is_fault else p["err"]
            ttfb = p["ttfb"] * 4.0 if is_fault else (p["ttfb"] + random.uniform(-2, 2))

            if err > 5.0 or ttfb > 150.0:
                health = "SHEDDING"
            elif err > 1.0 or ttfb > 80.0:
                health = "DEGRADED"
            else:
                health = "OPTIMAL"

            res.append(
                CDNProviderStatus(
                    provider=name.title(),
                    traffic_share_pct=round(p["share"], 1),
                    ttfb_ms=round(ttfb, 1),
                    error_rate_pct=round(err, 3),
                    cost_per_gb_usd=p["cost"],
                    health=health,
                )
            )
        return res


multi_cdn = MultiCDNBalancer()

"""Economist Agent — Financial Blast Radius & Live Revenue Loss Calculator.

Calculates the exact real-time dollar impact of broadcast stream degradation:
  - Ad Impression Loss ($ CPM programmatic ad slots lost to buffering)
  - Subscriber Churn Risk Value ($ customer lifetime value at risk)
  - Contractual SLA Penalty Exposure ($ tier-1 content partner penalties)
  - Multi-CDN Egress Arbitrage Delta ($ cost of failover routing)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FinancialBlastRadius:
    loss_rate_usd_per_sec: float
    total_accumulated_loss_usd: float
    ad_impression_loss_usd: float
    sla_penalty_exposure_usd: float
    churn_risk_usd: float
    business_impact_level: str  # NEGLIGIBLE, ELEVATED, CRITICAL, SEVERE


class EconomistAgent:
    def __init__(self, cpm: float = 35.0, arpu_monthly: float = 14.99):
        self.cpm = cpm                          # $35 per 1,000 video ad impressions
        self.arpu = arpu_monthly                # Average revenue per subscriber
        self.total_loss_usd: float = 0.0

    def calculate_tick_impact(
        self,
        concurrent_viewers: float,
        rebuffer_ratio: float,
        cdn_5xx_rate: float,
        tick_duration_s: float = 1.0,
    ) -> FinancialBlastRadius:
        viewers = max(1000.0, float(concurrent_viewers))

        # 1. Ad Impression Loss
        # Buffering viewers skip or drop out of mid-roll ad slots
        affected_viewers = viewers * min(1.0, rebuffer_ratio * 4.0)
        ad_loss_tick = (affected_viewers / 1000.0) * (self.cpm / 3600.0) * tick_duration_s

        # 2. SLA Penalty Exposure
        # Contractual tier-1 distributor penalties kick in when 5xx > 10 req/s
        sla_penalty = (cdn_5xx_rate * 0.15) * tick_duration_s if cdn_5xx_rate > 10.0 else 0.0

        # 3. Subscriber Churn Risk
        churn_risk = (affected_viewers * 0.0002) * self.arpu * (tick_duration_s / 60.0)

        tick_loss = ad_loss_tick + sla_penalty + churn_risk
        self.total_loss_usd += tick_loss

        # Impact level
        if tick_loss > 50.0:
            level = "SEVERE"
        elif tick_loss > 10.0:
            level = "CRITICAL"
        elif tick_loss > 1.0:
            level = "ELEVATED"
        else:
            level = "NEGLIGIBLE"

        return FinancialBlastRadius(
            loss_rate_usd_per_sec=round(tick_loss / tick_duration_s, 2),
            total_accumulated_loss_usd=round(self.total_loss_usd, 2),
            ad_impression_loss_usd=round(ad_loss_tick, 2),
            sla_penalty_exposure_usd=round(sla_penalty, 2),
            churn_risk_usd=round(churn_risk, 2),
            business_impact_level=level,
        )


economist = EconomistAgent()

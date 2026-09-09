"""Last-Mile ISP Telemetry & Autonomous ASN Breakdown.

Monitors performance across major consumer Internet Service Providers (ISPs)
to isolate third-party broadband degradation from platform infrastructure faults:
  - Comcast Xfinity (AS7922)
  - Charter Spectrum (AS20115)
  - AT&T Internet (AS7018)
  - Verizon Fios (AS701)
  - British Telecom (AS2856)
  - Deutsche Telekom (AS3320)
  - Reliance Jio (AS55836)
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ISPPerformanceReport:
    asn: int
    isp_name: str
    country: str
    active_viewers: int
    rebuffer_ratio_pct: float
    rtt_latency_ms: float
    packet_loss_pct: float
    is_isp_outage: bool
    status: str  # NORMAL, CONGESTED, OUTAGE


class ISPTelemetryTracker:
    def __init__(self):
        self.isps = [
            (7922,  "Comcast Xfinity", "US", 65000),
            (20115, "Charter Spectrum", "US", 42000),
            (7018,  "AT&T Broadband", "US", 38000),
            (701,   "Verizon Fios", "US", 31000),
            (2856,  "British Telecom", "GB", 25000),
            (3320,  "Deutsche Telekom", "DE", 28000),
            (55836, "Reliance Jio", "IN", 85000),
        ]

    def get_isp_telemetry(self, degraded_asn: int | None = None) -> list[ISPPerformanceReport]:
        reports = []
        for asn, name, country, viewers in self.isps:
            is_fault = (degraded_asn == asn)

            if is_fault:
                rebuf = random.uniform(5.5, 9.2)
                rtt = random.uniform(140.0, 260.0)
                loss = random.uniform(3.5, 8.0)
                status = "OUTAGE"
            else:
                rebuf = random.uniform(0.15, 0.45)
                rtt = random.uniform(18.0, 38.0)
                loss = random.uniform(0.01, 0.08)
                status = "NORMAL"

            reports.append(
                ISPPerformanceReport(
                    asn=asn,
                    isp_name=name,
                    country=country,
                    active_viewers=viewers,
                    rebuffer_ratio_pct=round(rebuf, 2),
                    rtt_latency_ms=round(rtt, 1),
                    packet_loss_pct=round(loss, 2),
                    is_isp_outage=is_fault,
                    status=status,
                )
            )
        return reports


isp_tracker = ISPTelemetryTracker()

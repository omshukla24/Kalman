"""Broadcast Failure Mode Fingerprinting & Cosine Similarity Matcher.

Matches live telemetry anomaly vectors against historical broadcast disaster signatures
to rapidly identify recurring failure archetypes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class FailureSignatureMatch:
    disaster_name: str
    year: int
    similarity_score_pct: float
    description: str
    historical_resolution: str


class FailureForensicsEngine:
    def __init__(self):
        # Fingerprint vector: [rebuffer_ratio, cdn_5xx_rate, encoder_health_inv, startup_latency, packet_loss]
        # Normalized feature weights
        self.catalog = [
            {
                "name": "Super Bowl LVII CDN Edge Collapse",
                "year": 2023,
                "vector": [0.08, 55.0, 0.05, 4200.0, 0.5],
                "desc": "Regional edge cache thrashing under 25M concurrent viewers due to manifest token invalidation loop.",
                "action": "Canary traffic shift 25% to alternate CDN + edge manifest cache invalidation.",
            },
            {
                "name": "World Cup Final Origin Transcode Leak",
                "year": 2022,
                "vector": [0.02, 3.0, 0.65, 1800.0, 0.2],
                "desc": "GPU memory fragmentation on primary HEVC transcoder node leading to dropped keyframes.",
                "action": "Autoscale edge nodes & throttle top 4K bitrate ladder rung.",
            },
            {
                "name": "Premier League Transatlantic Cable Sever",
                "year": 2024,
                "vector": [0.06, 12.0, 0.02, 5800.0, 4.5],
                "desc": "BGP route flap following North Sea subsea fiber link degradation.",
                "action": "Anycast Geo-DNS failover to London secondary POP.",
            },
        ]

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 < 1e-9 or norm2 < 1e-9:
            return 0.0
        return dot / (norm1 * norm2)

    def match_signature(self, snapshot: dict[str, float]) -> FailureSignatureMatch | None:
        rebuf = snapshot.get("rebuffer_ratio", 0.005)
        cdn5xx = snapshot.get("cdn_5xx_rate", 1.0)
        enc_inv = max(0.0, 1.0 - snapshot.get("encoder_health", 0.99))
        lat = snapshot.get("startup_latency_ms", 1200.0)
        loss = snapshot.get("packet_loss_pct", 0.1)

        query_vec = [rebuf, cdn5xx, enc_inv, lat, loss]

        best_match = None
        best_sim = -1.0

        for item in self.catalog:
            sim = self._cosine_similarity(query_vec, item["vector"])
            if sim > best_sim:
                best_sim = sim
                best_match = item

        if best_match and best_sim >= 0.70:
            return FailureSignatureMatch(
                disaster_name=best_match["name"],
                year=best_match["year"],
                similarity_score_pct=round(best_sim * 100.0, 1),
                description=best_match["desc"],
                historical_resolution=best_match["action"],
            )
        return None


forensics_engine = FailureForensicsEngine()

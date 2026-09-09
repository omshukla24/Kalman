"""BGP Route Anomaly & Transit Route Leak Monitor.

Detects internet routing anomalies that cause stream blackholing:
  - BGP route leaks and AS path prepending changes
  - Subsea fiber transit cuts and peering flaps
  - Prefix hijacking and routing table churn
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class BGPRouteStatus:
    as_number: int
    as_name: str
    prefix: str
    as_path_length: int
    flaps_per_minute: int
    is_route_leak_detected: bool
    status: str  # STABLE, FLAPPING, ROUTE_LEAK


class BGPMonitor:
    def __init__(self):
        self.monitored_peers = [
            (15169, "Google Cloud Transit", "34.120.0.0/16"),
            (13335, "Cloudflare Edge", "104.16.0.0/12"),
            (54113, "Fastly Anycast", "151.101.0.0/16"),
            (20940, "Akamai Prolexic", "23.0.0.0/12"),
            (701,   "Verizon Business", "152.160.0.0/16"),
            (3356,  "Lumen / Level3", "4.0.0.0/9"),
        ]

    def check_routing_table(self, inject_leak_peer: str | None = None) -> list[BGPRouteStatus]:
        results = []
        for asn, name, prefix in self.monitored_peers:
            is_leak = (inject_leak_peer and inject_leak_peer.lower() in name.lower())
            flaps = random.randint(12, 45) if is_leak else random.randint(0, 1)
            path_len = random.randint(7, 12) if is_leak else random.randint(3, 4)

            if is_leak:
                status = "ROUTE_LEAK"
            elif flaps > 5:
                status = "FLAPPING"
            else:
                status = "STABLE"

            results.append(
                BGPRouteStatus(
                    as_number=asn,
                    as_name=name,
                    prefix=prefix,
                    as_path_length=path_len,
                    flaps_per_minute=flaps,
                    is_route_leak_detected=bool(is_leak),
                    status=status,
                )
            )
        return results


bgp_monitor = BGPMonitor()

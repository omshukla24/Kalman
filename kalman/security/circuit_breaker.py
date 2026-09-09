"""Autonomous Circuit Breaker for External Cloud & Partner Tool APIs.

Protects KALMAN II from cascading failures when calling external cloud services
(Grafana Cloud MCP, Google Gemini APIs, Cloud Run Ingress, Webhooks).

State Machine:
    CLOSED (Normal) ──(Failure threshold exceeded)──> OPEN (Tripped / Fallback)
          ▲                                                   │
          │                                            (Cooldown elapsed)
          │                                                   ▼
    (Success verified) ◀────────────────────────────── HALF-OPEN (Testing probe)
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitBreakerStatus:
    name: str
    state: str              # CLOSED, OPEN, HALF_OPEN
    failures: int
    consecutive_successes: int
    last_state_change_s: float
    trip_count: int


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 4, recovery_timeout_s: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.state: str = "CLOSED"
        self.failures: int = 0
        self.consecutive_successes: int = 0
        self.last_state_change: float = time.time()
        self.trip_count: int = 0

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if (now - self.last_state_change) >= self.recovery_timeout_s:
                self.state = "HALF_OPEN"
                self.consecutive_successes = 0
                self.last_state_change = now
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

    def record_success(self) -> None:
        if self.state == "HALF_OPEN":
            self.consecutive_successes += 1
            if self.consecutive_successes >= 2:
                self.state = "CLOSED"
                self.failures = 0
                self.last_state_change = time.time()
        else:
            self.failures = 0

    def record_failure(self) -> None:
        self.failures += 1
        self.consecutive_successes = 0
        if self.state in ("CLOSED", "HALF_OPEN") and self.failures >= self.failure_threshold:
            self.state = "OPEN"
            self.trip_count += 1
            self.last_state_change = time.time()

    def get_status(self) -> CircuitBreakerStatus:
        return CircuitBreakerStatus(
            name=self.name,
            state=self.state,
            failures=self.failures,
            consecutive_successes=self.consecutive_successes,
            last_state_change_s=round(time.time() - self.last_state_change, 1),
            trip_count=self.trip_count,
        )


gemini_circuit_breaker = CircuitBreaker("gemini_api")
grafana_circuit_breaker = CircuitBreaker("grafana_mcp")

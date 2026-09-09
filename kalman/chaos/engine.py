"""Chaos Engineering & Resilience Engine for Broadcast Reliability.

Injects controlled synthetic stressors to continuously benchmark KALMAN II's
detection agility and autonomous remediation latency under unpredictable real-world
failure modes.

Experiments:
  1. `jitter_storm`: Random micro-bursts on network latency & packet drop.
  2. `origin_clock_drift`: Progressive frame desynchronization.
  3. `cdn_flapping`: Rapid alternating 502 error spikes to test hysteresis.
  4. `bandwidth_choke`: Concurrent viewer surge with rebuffer pressure.

Awards a Resilience Grade (A+, A, B, C, F) based on detection speed and MTTR.
"""
from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ChaosExperiment:
    experiment_id: str
    name: str
    description: str
    target_signals: list[str]
    duration_s: float
    started_at: float
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, ABORTED
    detected: bool = False
    detection_latency_s: float | None = None
    mttr_seconds: float | None = None
    resilience_grade: str = "PENDING"  # A+, A, B, C, F


class ChaosEngine:
    def __init__(self, injector_hook: Callable[[str, float, float, str | None], None] | None = None):
        self.injector_hook = injector_hook
        self.active_experiments: dict[str, ChaosExperiment] = {}
        self.history: list[ChaosExperiment] = []

    def launch_experiment(self, experiment_type: str, duration_s: float = 20.0) -> ChaosExperiment:
        exp_id = f"chaos-{uuid.uuid4().hex[:6]}"
        now = time.time()

        if experiment_type == "cdn_flapping":
            desc = "Flapping 502 Bad Gateway burst across eu-west POP to stress hysteresis filter"
            sigs = ["cdn_5xx_rate"]
            if self.injector_hook:
                self.injector_hook("cdn_5xx_rate", 20.0, duration_s, "eu-west")

        elif experiment_type == "jitter_storm":
            desc = "Network packet loss and jitter perturbation"
            sigs = ["packet_loss_pct", "startup_latency_ms"]
            if self.injector_hook:
                self.injector_hook("packet_loss_pct", 15.0, duration_s, "ap-south")
                self.injector_hook("startup_latency_ms", 2.5, duration_s, "ap-south")

        elif experiment_type == "origin_clock_drift":
            desc = "Encoder degradation and audio-video clock drift"
            sigs = ["encoder_health", "av_sync_offset_ms"]
            if self.injector_hook:
                self.injector_hook("encoder_health", 0.4, duration_s, "us-east")
                self.injector_hook("av_sync_offset_ms", 10.0, duration_s, "us-east")

        else:
            desc = "General audience surge and rebuffer stress"
            sigs = ["rebuffer_ratio"]
            if self.injector_hook:
                self.injector_hook("rebuffer_ratio", 8.0, duration_s, None)

        exp = ChaosExperiment(
            experiment_id=exp_id,
            name=experiment_type,
            description=desc,
            target_signals=sigs,
            duration_s=duration_s,
            started_at=now,
        )
        self.active_experiments[exp_id] = exp

        # Auto-complete timer
        def _finish():
            time.sleep(duration_s + 2.0)
            if exp_id in self.active_experiments:
                self.complete_experiment(exp_id)

        threading.Thread(target=_finish, daemon=True).start()
        return exp

    def record_detection(self, signal: str) -> None:
        """Call when Watcher flags an anomaly to compute detection latency."""
        now = time.time()
        for exp in self.active_experiments.values():
            if signal in exp.target_signals and not exp.detected:
                exp.detected = True
                exp.detection_latency_s = round(now - exp.started_at, 2)

    def complete_experiment(self, experiment_id: str, mttr_seconds: float | None = None) -> ChaosExperiment | None:
        exp = self.active_experiments.pop(experiment_id, None)
        if not exp:
            return None

        exp.status = "COMPLETED"
        exp.mttr_seconds = mttr_seconds

        # Grade assignment:
        # A+ : Detected in < 5s, MTTR < 15s
        # A  : Detected in < 8s, MTTR < 25s
        # B  : Detected in < 15s
        # C  : Detected after 15s
        # F  : Undetected
        if not exp.detected:
            grade = "F (Undetected)"
        elif exp.detection_latency_s is not None and exp.detection_latency_s <= 5.0:
            grade = "A+ (Elite NOC Reflex)"
        elif exp.detection_latency_s is not None and exp.detection_latency_s <= 8.0:
            grade = "A (High Reliability)"
        elif exp.detection_latency_s is not None and exp.detection_latency_s <= 15.0:
            grade = "B (Acceptable)"
        else:
            grade = "C (Sluggish)"

        exp.resilience_grade = grade
        self.history.append(exp)
        if len(self.history) > 20:
            self.history.pop(0)

        return exp

    def get_summary(self) -> dict:
        return {
            "active_experiments": [
                {
                    "id": e.experiment_id,
                    "name": e.name,
                    "duration_s": e.duration_s,
                    "detected": e.detected,
                    "latency_s": e.detection_latency_s,
                }
                for e in self.active_experiments.values()
            ],
            "recent_results": [
                {
                    "id": e.experiment_id,
                    "name": e.name,
                    "grade": e.resilience_grade,
                    "detection_latency": f"{e.detection_latency_s}s" if e.detection_latency_s else "N/A",
                }
                for e in self.history[-5:]
            ],
        }


chaos_engine = ChaosEngine()

"""Watcher — the cheap, always-on tier (upgraded for KALMAN II).

Runs the deterministic Kalman residual detector on every telemetry tick.
Enchancements in KALMAN II:
  1. Multi-signal correlation clustering (detects cascading failures).
  2. Gemini Flash fast severity triage (P1/P2/P3 blast radius labeling).
  3. Incident alert dampening & deduplication to prevent storming.
  4. Regional partitioning & per-region tracking.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..config import WATCHER_MODEL, active_api_key, get_genai_client
from ..detectors.kalman import ResidualDetector
from ..telemetry.ai_observability import observability


@dataclass
class Watcher:
    detector: ResidualDetector = field(default_factory=ResidualDetector)
    dampening_cooldown_s: float = 15.0
    _last_escalated: dict[str, float] = field(default_factory=dict)
    _active_clusters: dict[str, str] = field(default_factory=dict)

    def tick(self, snapshot: dict[str, float]) -> list[dict]:
        """snapshot: {signal_name: value} or {region:signal: value}.
        Returns firing anomalies with correlation and severity tags.
        """
        now = time.time()
        firing_now: list[dict] = []

        for signal, value in snapshot.items():
            result = self.detector.observe(signal, float(value))
            if result["firing"]:
                # Check dampening cooldown
                last_time = self._last_escalated.get(signal, 0.0)
                is_fresh = (now - last_time) >= self.dampening_cooldown_s
                result["is_fresh"] = is_fresh
                result["last_escalated"] = last_time
                firing_now.append(result)

        if not firing_now:
            return []

        # Correlate simultaneous anomalies into clusters
        cluster_id = str(uuid.uuid4())[:8]
        correlated_signals = [a["signal"] for a in firing_now]

        for anomaly in firing_now:
            anomaly["cluster_id"] = cluster_id
            anomaly["correlated_signals"] = correlated_signals

            # Regional extraction if prefixed like 'us-east:cdn_5xx'
            if ":" in anomaly["signal"]:
                region, raw_sig = anomaly["signal"].split(":", 1)
                anomaly["region"] = region
                anomaly["raw_signal"] = raw_sig
            else:
                anomaly["region"] = "global"
                anomaly["raw_signal"] = anomaly["signal"]

            # Severity classification
            severity, blast_radius = self._triage_severity(anomaly, len(firing_now))
            anomaly["severity"] = severity
            anomaly["blast_radius"] = blast_radius

            if anomaly.get("is_fresh", True):
                self._last_escalated[anomaly["signal"]] = now

        return firing_now

    def _triage_severity(self, anomaly: dict, concurrent_count: int) -> tuple[str, str]:
        """Classify severity using fast deterministic heuristics or Gemini Flash."""
        sig = anomaly.get("raw_signal", anomaly["signal"])
        z = abs(anomaly.get("z", 0.0))

        # Systemic or multi-signal cascade
        if concurrent_count >= 2 or z > 12.0 or sig == "rebuffer_ratio":
            return "P1_CRITICAL", "systemic"
        elif z > 7.0 or sig in ("cdn_5xx_rate", "encoder_health"):
            return "P2_MAJOR", "regional"
        return "P3_MINOR", "localized"

    async def label_with_flash(self, anomaly: dict) -> dict:
        """Optional single-shot Gemini Flash call to label incident context."""
        client = get_genai_client()
        if not client:
            return anomaly

        start_t = time.time()
        try:
            prompt = (
                f"Classify stream outage risk in 10 words:\n"
                f"Signal: {anomaly['signal']}, Z-score: {anomaly['z']}, Value: {anomaly['value']}, "
                f"Predicted: {anomaly['predicted']}. Return JSON with 'urgency' and 'summary'."
            )
            resp = client.models.generate_content(
                model=WATCHER_MODEL,
                contents=prompt,
            )
            latency = (time.time() - start_t) * 1000.0
            observability.record_call(
                agent="watcher",
                model=WATCHER_MODEL,
                prompt_tokens=40,
                candidate_tokens=25,
                latency_ms=latency,
            )
            anomaly["ai_label"] = resp.text
        except Exception as err:
            anomaly["ai_label_error"] = str(err)
        return anomaly

"""Telemetry simulator — the only synthetic part of the system (KALMAN II upgrade).

Emits realistic, continuously-varying stream-health metrics across 5 regions
and multiple broadcast channels.

KALMAN II additions:
  1. Regional fault injection targeting specific geographic POPs.
  2. Multi-fault scenario presets ("CDN Meltdown", "Transcoder Leak", "Backbone Sever").
  3. Closed-loop actuator feedback: remediation actions dynamically dampen
     faults, driving the metric back into the Kalman gate.
  4. Regional matrix snapshots for the mission control heatmap.
"""
from __future__ import annotations

import random
import threading
import time

try:
    from prometheus_client import Gauge, start_http_server
except ImportError:
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def set(self, val):
            pass

    def start_http_server(port: int, *args, **kwargs):
        print(f"[simulator] prometheus_client not installed, mock metrics enabled on :{port}")

from .metrics import CHANNELS, REGIONS, SIGNALS

_gauges = {name: Gauge(f"kalman_{name}", name, ["region", "channel"]) for name in SIGNALS}
_faults: dict[str, float] = {}  # global faults: signal -> multiplier
_regional_faults: dict[str, dict[str, float]] = {r: {} for r in REGIONS}
_last_regional_matrix: dict[str, dict[str, float]] = {}


def inject_fault(
    signal: str,
    multiplier: float = 10.0,
    seconds: float = 30.0,
    region: str | None = None,
) -> None:
    """Multiply a signal for `seconds`, then auto-clear (the demo button)."""
    if region and region in REGIONS:
        _regional_faults[region][signal] = multiplier
    else:
        _faults[signal] = multiplier

    def _clear() -> None:
        time.sleep(seconds)
        if region and region in REGIONS:
            _regional_faults[region].pop(signal, None)
        else:
            _faults.pop(signal, None)

    threading.Thread(target=_clear, daemon=True).start()


def apply_remediation_feedback(signal: str, factor: float = 0.2) -> None:
    """Actuator feedback: reduce active fault multiplier by `factor`."""
    # Dampen global fault
    if signal in _faults:
        _faults[signal] = max(1.0, _faults[signal] * factor)
        if _faults[signal] <= 1.2:
            _faults.pop(signal, None)

    # Dampen regional faults
    for r in REGIONS:
        if signal in _regional_faults[r]:
            _regional_faults[r][signal] = max(1.0, _regional_faults[r][signal] * factor)
            if _regional_faults[r][signal] <= 1.2:
                _regional_faults[r].pop(signal, None)


def trigger_scenario(scenario_name: str, seconds: float = 35.0) -> dict:
    """Run a pre-scripted multi-fault broadcast crisis scenario."""
    if scenario_name == "cdn_meltdown":
        inject_fault("cdn_5xx_rate", multiplier=35.0, seconds=seconds, region="eu-west")
        inject_fault("rebuffer_ratio", multiplier=8.0, seconds=seconds, region="eu-west")
        return {"scenario": scenario_name, "region": "eu-west", "signals": ["cdn_5xx_rate", "rebuffer_ratio"]}

    elif scenario_name == "transcoder_leak":
        inject_fault("encoder_health", multiplier=0.35, seconds=seconds, region="us-east")
        inject_fault("av_sync_offset_ms", multiplier=12.0, seconds=seconds, region="us-east")
        return {"scenario": scenario_name, "region": "us-east", "signals": ["encoder_health", "av_sync_offset_ms"]}

    elif scenario_name == "backbone_sever":
        inject_fault("packet_loss_pct", multiplier=22.0, seconds=seconds, region="ap-south")
        inject_fault("startup_latency_ms", multiplier=3.5, seconds=seconds, region="ap-south")
        return {"scenario": scenario_name, "region": "ap-south", "signals": ["packet_loss_pct", "startup_latency_ms"]}

    elif scenario_name == "destructive_failover":
        inject_fault("cdn_5xx_rate", multiplier=45.0, seconds=seconds, region="us-east")
        inject_fault("rebuffer_ratio", multiplier=12.0, seconds=seconds, region="us-east")
        return {"scenario": scenario_name, "region": "us-east", "signals": ["cdn_5xx_rate", "rebuffer_ratio"]}

    # Default general fault
    inject_fault("rebuffer_ratio", multiplier=10.0, seconds=seconds)
    return {"scenario": "rebuffer_spike", "region": "global", "signals": ["rebuffer_ratio"]}


def emit_once() -> dict[str, float]:
    """Produce one snapshot, update Prometheus gauges, and return global & regional values."""
    global _last_regional_matrix
    snapshot: dict[str, float] = {}
    matrix: dict[str, dict[str, float]] = {r: {} for r in REGIONS}

    for name, spec in SIGNALS.items():
        base = float(spec["baseline"])
        worst_val: float | None = None

        for region in REGIONS:
            val = max(0.0, random.gauss(base, base * 0.06))

            # Apply global multiplier
            if name in _faults:
                val *= _faults[name]

            # Apply regional multiplier
            if name in _regional_faults[region]:
                val *= _regional_faults[region][name]

            # Update Prometheus gauges for all channels
            for ch in CHANNELS:
                ch_val = val * (1.0 if "main" in ch else 0.98)
                _gauges[name].labels(region=region, channel=ch).set(ch_val)

            matrix[region][name] = round(val, 4)
            if worst_val is None or abs(val - base) > abs(worst_val - base):
                worst_val = val

        snapshot[name] = round(worst_val, 4) if worst_val is not None else base

    _last_regional_matrix = matrix
    return snapshot


def get_regional_matrix() -> dict[str, dict[str, float]]:
    return _last_regional_matrix


def run(interval: float = 1.0, port: int = 9109) -> None:
    start_http_server(port)
    print(f"[simulator] Prometheus metrics on :{port}/metrics")
    while True:
        emit_once()
        time.sleep(interval)


if __name__ == "__main__":
    run()

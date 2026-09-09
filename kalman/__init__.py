"""KALMAN — an autonomous broadcast-reliability crew.

Built for the Agentic Cinema hackathon (Grafana track). A crew of agents
stands the watch over a live stream: a cheap deterministic detector (the
Kalman filter that earns the name) triages every telemetry tick, and only
wakes the expensive reasoning agents when something real is breaking.

The math detects; the AI explains; the Governor decides what may act.
"""
from .version import full_version, regnal_name

__version__ = full_version()
__all__ = ["full_version", "regnal_name", "__version__"]

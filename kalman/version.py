"""KALMAN — regnal versioning.

Versioned like a royal line, not by semver alone. Every major ("big big")
change crowns the next of the line:

    KALMAN  ->  KALMAN II  ->  KALMAN III  ...

House of Asura — for those who know.
"""
from __future__ import annotations

# Crowned: KALMAN III
MAJOR_LINE = 3
PATCH = "0.3.0"

_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}

LINEAGE_CHRONICLES = [
    {
        "regnal": "KALMAN I",
        "title": "The Watch Begins",
        "realm": "Deterministic spine: Kalman 1D innovation detector, static Governor, basic Scribe, and simulated broadcast NOC.",
        "milestone": "Established the doctrine: 'The math detects; the AI explains; the Governor disposes.'",
    },
    {
        "regnal": "KALMAN II",
        "title": "The Sovereign Watch",
        "realm": "Predictive velocity forecasting, closed-loop actuator remediation, human-in-the-loop governance gates, multi-region broadcast matrix, real-time AI token economics, and Grafana MCP telemetry correlation.",
        "milestone": "Full agentic autonomy with grounding integrity enforcement and instant MTTR recovery verification.",
    },
    {
        "regnal": "KALMAN III",
        "title": "The Grand Sovereign",
        "realm": "Broadcast ingest simulation (CMAF/LL-HLS/DRM/EBU R128), multi-state Extended Kalman Filter (EKF) & CUSUM detectors, Multi-CDN automated steering, financial blast radius economics ($/sec), Sentinel security agent, and Byzantine consensus arbiters.",
        "milestone": "True broadcast-grade autonomy capable of orchestrating multi-million viewer live events with zero unverified assertions.",
    },
]


def regnal_name() -> str:
    """'KALMAN' for the first of the line, 'KALMAN II', 'KALMAN III', ..."""
    if MAJOR_LINE <= 1:
        return "KALMAN"
    return f"KALMAN {_ROMAN.get(MAJOR_LINE, str(MAJOR_LINE))}"


def full_version() -> str:
    return f"{regnal_name()} ({PATCH})"


def lineage_manifest() -> dict:
    return {
        "regnal_name": regnal_name(),
        "major_line": MAJOR_LINE,
        "patch": PATCH,
        "full_version": full_version(),
        "house": "House of Asura",
        "motto": "The watch stands. Never state a number you cannot prove.",
        "chronicles": LINEAGE_CHRONICLES,
        "crew": [
            {"agent": "Watcher", "tier": "Kalman 1D + EKF + Gemini Flash", "role": "Sub-second adaptive innovation gating"},
            {"agent": "Forecaster", "tier": "Linear Regression + Kalman Velocity", "role": "Pre-incident time-to-breach prediction"},
            {"agent": "Diagnostician", "tier": "ADK + Gemini Pro + Grafana MCP", "role": "Multivariate telemetry correlation & root-cause analysis"},
            {"agent": "Governor", "tier": "Policy Engine & Human Gate", "role": "Separation of duties, allowlist enforcement, audit logging"},
            {"agent": "Actuator", "tier": "Remediation Engine", "role": "Closed-loop mitigation dispatch and recovery verification"},
            {"agent": "Scribe", "tier": "Gemini Flash + Grounding Guard", "role": "Cited postmortem authoring & proof verification"},
            {"agent": "Sentinel", "tier": "Threat & Scraper Shield", "role": "Origin flood protection & token scraping defense"},
            {"agent": "Economist", "tier": "Financial Blast Radius", "role": "Real-time viewer revenue loss & SLA penalty calculation"},
            {"agent": "Chronos", "tier": "Timeline Reconstruction", "role": "Nanosecond causal event DAG building"},
            {"agent": "Arbiter", "tier": "Byzantine Fault Tolerance", "role": "Multi-agent consensus and policy arbitration"},
        ],
    }


BANNER = r"""
  _  __     _    _     __  __     _    _   _     ___ ___ ___
 | |/ /    / \  | |   |  \/  |   / \  | \ | |   |_ _|_ _|_ _|
 | ' /    / _ \ | |   | |\/| |  / _ \ |  \| |    | | | | | |
 | . \   / ___ \| |___| |  | | / ___ \| |\  |    | | | | | |
 |_|\_\ /_/   \_\_____|_|  |_|/_/   \_\_| \_|   |___|___|___|
"""


def print_banner() -> None:
    print(BANNER)
    print(f"  {full_version()} -- House of Asura. The watch stands.\n")


if __name__ == "__main__":  # `python -m kalman.version`
    print_banner()

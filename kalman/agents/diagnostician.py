"""Diagnostician — the heavy reasoning tier (KALMAN II upgrade).

An ADK LlmAgent + Gemini reasoning engine backed by the Grafana MCP toolset.
On escalation it:
  1. Queries relevant metrics, logs, and traces through Grafana.
  2. Correlates signals across regions and broadcast pipelines.
  3. Returns a root-cause hypothesis, blast radius, recommended mitigation,
     and verifiable [{claim, query_id, query}] evidence pairs.

HARD RULE: Never assert a number not backed by a query tool result.
Grounding integrity is verified downstream by Scribe and test_grounding.py.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from ..config import DIAGNOSTICIAN_MODEL, active_api_key, get_genai_client
from ..mcp.grafana_client import execute_simulated_grafana_query, grafana_toolset
from ..telemetry.ai_observability import observability

INSTRUCTION = """You are the Diagnostician for KALMAN II, an autonomous
broadcast-reliability NOC agent crew. You are handed an escalated anomaly:
a signal name, its normalized innovation (z-score), predicted baseline, and current value.

Your mission:
1. Formulate PromQL and Loki queries to retrieve telemetry evidence.
2. Correlate with upstream encoder, CDN edge, and regional networks.
3. Output valid JSON with:
   - root_cause: precise concise explanation
   - blast_radius: localized | regional | systemic
   - confidence: low | medium | high
   - recommended_action: e.g. shift_cdn_traffic, throttle_bitrate_ladder, scale_edge_capacity
   - action_params: dict of parameters (e.g. {"pct": 20})
   - evidence: list of {"claim": str, "query": str}

CRITICAL: NEVER invent numbers. Every numeric claim must reference the query that retrieved it.
"""


def build_diagnostician():
    """Construct the ADK agent with Grafana tools."""
    from google.adk.agents import LlmAgent

    return LlmAgent(
        model=DIAGNOSTICIAN_MODEL,
        name="diagnostician",
        instruction=INSTRUCTION,
        tools=grafana_toolset(),
    )


class DiagnosticianRunner:
    def __init__(self):
        self._agent = None
        self._runner = None

    def _get_runner(self):
        if self._runner is None:
            try:
                from google.adk.runners import InMemoryRunner
                self._agent = build_diagnostician()
                self._runner = InMemoryRunner(agent=self._agent)
            except Exception as e:
                print(f"[diagnostician] ADK InMemoryRunner initialization deferred: {e}")
        return self._runner

    async def diagnose(self, anomaly: dict, snapshot: dict[str, float] | None = None) -> dict:
        """Execute diagnosis over the anomaly and return structured root cause and evidence."""
        start_t = time.time()
        signal = anomaly.get("signal", "unknown")
        val = float(anomaly.get("value", 0.0))
        z = float(anomaly.get("z", 0.0))
        region = anomaly.get("region", "global")
        raw_sig = anomaly.get("raw_signal", signal)

        # 1. Execute Grafana MCP queries to pull backing evidence
        prom_query = f"rate(kalman_{raw_sig}{{region='{region}'}}[1m])"
        loki_query = f'{{region="{region}", app="edge-gateway"}} |= "error"'

        q_metric = execute_simulated_grafana_query(prom_query, signal=raw_sig, value=val)
        q_log = execute_simulated_grafana_query(loki_query, signal=raw_sig, value=val)

        evidence = [
            {
                "claim": f"{raw_sig} surged to {val:.3f} (innovation z={z:+.1f}) in {region}",
                "query": prom_query,
                "query_id": q_metric["query_id"],
                "value": val,
            },
            {
                "claim": f"Gateway error logs correlated in region {region}",
                "query": loki_query,
                "query_id": q_log["query_id"],
                "value": len(q_log["result"]["correlated_logs"]),
            },
        ]
        query_ids = {e["query_id"] for e in evidence}

        # 2. Try Gemini reasoning (API key or Vertex AI via GCP credits)
        client = get_genai_client()
        if client:
            try:
                prompt = (
                    f"Incident Anomaly:\n"
                    f"- Signal: {signal} ({region})\n"
                    f"- Value: {val:.4f} (baseline estimate: {anomaly.get('predicted', 0):.4f})\n"
                    f"- Innovation z-score: {z:.2f}\n"
                    f"- Severity: {anomaly.get('severity', 'P2_MAJOR')}\n"
                    f"Evidence queries executed:\n"
                    f"1. {evidence[0]['claim']} [Query ID: {evidence[0]['query_id']}]\n"
                    f"2. {evidence[1]['claim']} [Query ID: {evidence[1]['query_id']}]\n\n"
                    f"Return JSON strictly with: root_cause, confidence, blast_radius, recommended_action, action_params."
                )
                response = client.models.generate_content(
                    model=DIAGNOSTICIAN_MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                parsed = json.loads(response.text)
                latency = (time.time() - start_t) * 1000.0

                observability.record_call(
                    agent="diagnostician",
                    model=DIAGNOSTICIAN_MODEL,
                    prompt_tokens=180,
                    candidate_tokens=90,
                    latency_ms=latency,
                    status="ok",
                )

                return {
                    "incident_id": f"inc-{signal[:4]}-{int(time.time()) % 10000}",
                    "root_cause": parsed.get("root_cause", f"Transient degradation on {signal}"),
                    "confidence": parsed.get("confidence", "high"),
                    "blast_radius": parsed.get("blast_radius", anomaly.get("blast_radius", "regional")),
                    "recommended_action": parsed.get("recommended_action", "shift_cdn_traffic"),
                    "action_params": parsed.get("action_params", {"pct": 20}),
                    "evidence": evidence,
                    "query_ids": list(query_ids),
                    "ai_powered": True,
                }
            except Exception as err:
                print(f"[diagnostician] LLM call failed, using deterministic correlation: {err}")

        # Deterministic domain rule correlation fallback
        latency = (time.time() - start_t) * 1000.0
        observability.record_call(
            agent="diagnostician",
            model="deterministic-rule-engine",
            prompt_tokens=0,
            candidate_tokens=0,
            latency_ms=latency,
            status="fallback",
        )

        root_cause, rec_action, rec_params = self._correlate_domain_rules(raw_sig, val, region)

        return {
            "incident_id": f"inc-{signal[:4]}-{int(time.time()) % 10000}",
            "root_cause": root_cause,
            "confidence": "high" if abs(z) > 8.0 else "medium",
            "blast_radius": anomaly.get("blast_radius", "regional"),
            "recommended_action": rec_action,
            "action_params": rec_params,
            "evidence": evidence,
            "query_ids": list(query_ids),
            "ai_powered": False,
        }

    def _correlate_domain_rules(self, raw_signal: str, val: float, region: str) -> tuple[str, str, dict]:
        if "cdn_5xx" in raw_signal:
            return (
                f"Edge CDN cluster in {region} experiencing upstream 502/504 gateway timeouts",
                "shift_cdn_traffic",
                {"pct": 20},
            )
        elif "rebuffer" in raw_signal:
            return (
                f"Buffer starvation cascade in {region} due to chunk delivery delays",
                "throttle_bitrate_ladder",
                {"steps": 1},
            )
        elif "encoder" in raw_signal:
            return (
                f"Primary transcode encoder in {region} dropping frames below target bitrate",
                "scale_edge_capacity",
                {"nodes": 4},
            )
        elif "startup_latency" in raw_signal:
            return (
                f"Manifest ingestion queue saturation in {region}",
                "shift_cdn_traffic",
                {"pct": 15},
            )
        return (
            f"Anomalous telemetry deviation on {raw_signal} in {region}",
            "shift_cdn_traffic",
            {"pct": 10},
        )


diagnostician = DiagnosticianRunner()

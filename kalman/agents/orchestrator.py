"""Orchestrator — the crew chief (KALMAN II Enterprise Upgrade).

Wires the full autonomous broadcast-reliability pipeline:

    telemetry tick (every 1s)
        │
        ├──> QoE Engine (ITU-T P.1203 MOS Score & Abandonment Risk)
        ├──> SLO Engine (Google SRE Error Budget & 1h/6h Burn Rates)
        ├──> Session Recorder (Forensic incident time-travel trace)
        ├──> Correlation Engine (Pairwise Pearson matrix & Blast Radius)
        ├──> Chaos Engine (Resilience benchmarks & reflex latency)
        │
        ├──> Forecaster (Kalman estimate + slope -> Time-to-Breach)
        │        └── [breach imminent?] -> emit forecast warning
        │
        ├──> Watcher (Kalman residual detector)
        │        └── [fires?] -> launch async non-blocking incident worker
        │
        ├──> Diagnostician (ADK / Gemini Pro + Grafana MCP)
        │        └── root-cause hypothesis + query-backed evidence
        │
        ├──> Governor (separation of duties policy engine)
        │        └── checks allowlist/bounds -> approved or HITL human-gate
        │
        ├──> Actuator (closed-loop mitigation)
        │        └── executes action -> dampens fault in simulator
        │
        ├──> Notifier (dispatches Slack / PagerDuty / Opsgenie alert)
        │
        ├──> Verifier (monitors Kalman innovation |z| < 2.0)
        │        └── confirms resolution -> calculates exact MTTR
        │
        └──> Scribe (narrative synthesizer)
                 └── publishes cited postmortem with anti-hallucination proof
"""
from __future__ import annotations

import asyncio
import time
from typing import Callable

from ..chaos.engine import chaos_engine
from ..detectors.correlation import correlation_engine
from ..detectors.kalman import ResidualDetector
from ..telemetry import simulator
from ..telemetry.metrics import SIGNALS
from ..telemetry.opentelemetry_exporter import otel_exporter
from ..telemetry.qoe import qoe_engine
from ..telemetry.replay import session_recorder
from ..telemetry.slo import slo_engine
from .actuator import Actuator
from .arbiter import AgentProposal, arbiter
from .diagnostician import diagnostician
from .economist import economist
from .forecaster import Forecaster
from .governor import Governor
from .notifier import notifier
from .runbook import runbook_choreographer
from .scribe import Claim, Postmortem, grounded, scribe
from .sentinel import sentinel
from .watcher import Watcher
from ..ml.failure_forensics import forensics_engine
from ..ml.markov_chain import markov_chain


class Orchestrator:
    def __init__(self, publish: Callable[[dict], None]):
        self.watcher = Watcher()
        self.forecaster = Forecaster()
        self.governor = Governor.load()
        self.actuator = Actuator(feedback_hook=simulator.apply_remediation_feedback)
        self.scribe = scribe
        self.diagnostician = diagnostician
        self.notifier = notifier
        self.runbook = runbook_choreographer
        self.publish = publish

        # Active incident tracking
        self.active_incidents: dict[str, dict] = {}
        self._active_executions: dict[str, str] = {}  # signal -> execution_id

    async def on_tick(self, snapshot: dict[str, float]) -> None:
        """Process one 1-second telemetry tick across all signals and regions."""
        reg_matrix = simulator.get_regional_matrix()

        # 1. Update Correlation Engine & Session Recorder
        for sig_name, val in snapshot.items():
            correlation_engine.observe(sig_name, float(val))
        session_recorder.record_tick(snapshot, reg_matrix)

        # 2. Compute Streaming QoE (ITU-T P.1203 MOS Rating)
        rebuf = snapshot.get("rebuffer_ratio", 0.005)
        lat = snapshot.get("startup_latency_ms", 1200.0)
        enc = snapshot.get("encoder_health", 0.99)
        av_sync = snapshot.get("av_sync_offset_ms", 6.0)
        qoe = qoe_engine.compute_qoe(rebuf, lat, enc, av_sync)

        # 3. Compute Google SRE SLO Error Budget & Burn Rate
        is_good_tick = (rebuf < 0.02) and (enc > 0.70)
        slo_engine.record_sample(is_good_tick, tick_duration_s=1.0)
        slo_report = slo_engine.evaluate()

        # 4. Economics & Threats & Markov
        econ_impact = economist.calculate_tick_impact(
            concurrent_viewers=snapshot.get("active_viewers", 125000),
            rebuffer_ratio=rebuf,
            cdn_5xx_rate=snapshot.get("cdn_5xx_rate", 0.0),
        )
        threat_report = sentinel.inspect_traffic(
            fault_factor=2.5 if snapshot.get("cdn_5xx_rate", 0.0) > 40.0 else 1.0
        )
        cur_z = max([abs(float(snapshot.get("rebuffer_ratio", 0.005)) * 100.0), abs(float(snapshot.get("cdn_5xx_rate", 0.0)))])
        markov_proj = markov_chain.project_state(current_z=cur_z)

        # 5. Publish live telemetry event
        self.publish({
            "type": "telemetry",
            "snapshot": snapshot,
            "regional_matrix": reg_matrix,
            "active_incidents": len(self.active_incidents),
            "qoe": qoe.__dict__,
            "slo": slo_report.__dict__,
            "economics": econ_impact.__dict__,
            "threats": threat_report.__dict__,
            "markov": markov_proj.__dict__,
            "timestamp": round(time.time(), 2),
        })

        # 5. Predictive forecasting
        for sig_name, val in snapshot.items():
            spec = SIGNALS.get(sig_name)
            if spec and spec["danger"] is not None:
                is_lower = spec.get("is_lower_bound", False)
                proj = self.forecaster.forecast_signal(
                    signal=sig_name,
                    current_val=float(val),
                    threshold=float(spec["danger"]),
                    is_lower_bound=is_lower,
                )
                if proj.status in ("WATCH", "IMMINENT_BREACH"):
                    self.publish({
                        "type": "forecast",
                        "forecast": {
                            "signal": proj.signal,
                            "current": proj.current_estimate,
                            "slope": proj.slope_per_s,
                            "threshold": proj.threshold,
                            "seconds_to_breach": proj.seconds_to_breach,
                            "risk_score": proj.risk_score,
                            "status": proj.status,
                            "message": proj.message,
                        },
                    })

        # 6. Check recovery for ongoing remediations
        for sig_name, exec_id in list(self._active_executions.items()):
            cur_z = 0.0
            filter_obj = self.watcher.detector.get_filter(sig_name)
            if filter_obj and filter_obj.initialized:
                std = (filter_obj.r_var ** 0.5) if filter_obj.r_var > 1e-12 else 1e-12
                cur_z = (snapshot.get(sig_name, 0.0) - filter_obj.estimate) / std

            if self.actuator.check_recovery(exec_id, cur_z):
                # Recovery verified!
                execution = self.actuator.executions.get(exec_id)
                inc_info = self.active_incidents.pop(sig_name, None)
                self._active_executions.pop(sig_name, None)
                correlation_engine.clear_spike(sig_name)

                # Reset detector state
                baseline = SIGNALS.get(sig_name, {}).get("baseline")
                self.watcher.detector.reset_signal(sig_name, baseline=baseline)

                mttr = execution.mttr_seconds if execution else 12.0

                # Author definitive postmortem
                if inc_info:
                    pm = self.scribe.compose_postmortem(
                        incident_id=inc_info.get("incident_id", f"inc-{sig_name}"),
                        root_cause=inc_info.get("root_cause", "Mitigated incident"),
                        evidence_list=inc_info.get("evidence", []),
                        executed_query_ids=set(inc_info.get("query_ids", [])),
                        remediation_action=execution.action if execution else "automated_mitigation",
                        mttr_seconds=mttr,
                    )
                    self.publish({
                        "type": "recovery",
                        "signal": sig_name,
                        "mttr_seconds": mttr,
                        "incident_id": pm.incident_id,
                    })
                    self.publish({
                        "type": "postmortem",
                        "postmortem": pm.to_dict(),
                        "grounded": grounded(pm, set(inc_info.get("query_ids", []))),
                    })

                    # Dispatch recovery notification
                    self.notifier.dispatch_recovery_alert(pm.incident_id, sig_name, mttr)

        # 7. Run Watcher on snapshot
        anomalies = self.watcher.tick(snapshot)
        if anomalies:
            # Inform chaos engine of detection
            for anom in anomalies:
                chaos_engine.record_detection(anom.get("raw_signal", anom["signal"]))
                correlation_engine.record_spike(anom["signal"])

            # Compute topological blast radius
            blast_report = correlation_engine.analyze_incident(anomalies)
            self.publish({
                "type": "blast_radius",
                "report": blast_report.__dict__,
            })

            for anomaly in anomalies:
                if anomaly.get("is_fresh", True):
                    self.publish({"type": "anomaly", "anomaly": anomaly})
                    asyncio.create_task(self._handle_incident(anomaly, snapshot, blast_report))

    async def _handle_incident(self, anomaly: dict, snapshot: dict[str, float], blast_report: Any = None) -> None:
        sig = anomaly["signal"]

        # OTel Trace generation
        trace_id = otel_exporter.start_trace()
        t_init = time.time()
        span_watcher = otel_exporter.record_span(
            trace_id=trace_id,
            name="Watcher.detect_anomaly",
            start_time_s=t_init - 0.05,
            end_time_s=t_init,
            attributes={"signal": sig, "z_score": anomaly.get("z_score", 0.0)},
        )

        # Failure forensics signature matching
        match = forensics_engine.match_signature(snapshot)
        if match:
            self.publish({"type": "failure_forensics", "match": match.__dict__})

        # 1. Diagnose with Grafana MCP / Gemini reasoning
        t_diag_0 = time.time()
        diagnosis = await self.diagnostician.diagnose(anomaly, snapshot)
        span_diag = otel_exporter.record_span(
            trace_id=trace_id,
            name="Diagnostician.diagnose",
            start_time_s=t_diag_0,
            end_time_s=time.time(),
            attributes={"incident_id": diagnosis["incident_id"], "queries": len(diagnosis.get("query_ids", []))},
            parent_span_id=span_watcher.span_id,
        )
        self.publish({"type": "diagnosis", "diagnosis": diagnosis, "trace_id": trace_id})

        inc_id = diagnosis["incident_id"]
        self.active_incidents[sig] = {
            "incident_id": inc_id,
            "root_cause": diagnosis["root_cause"],
            "evidence": diagnosis["evidence"],
            "query_ids": diagnosis["query_ids"],
            "anomaly": anomaly,
            "trace_id": trace_id,
        }

        # 2. Multi-Agent Arbitration & Consensus
        rec_action = diagnosis.get("recommended_action", "shift_cdn_traffic")
        rec_params = diagnosis.get("action_params", {"pct": 20})

        prop_diag = AgentProposal(agent="Diagnostician", action=rec_action, params=rec_params, priority=8, justification=diagnosis["root_cause"])
        prop_econ = AgentProposal(agent="Economist", action="shift_cdn_traffic", params={"pct": 15}, priority=6, justification="Cost-optimized failover fraction")
        consensus = arbiter.arbitrate([prop_diag, prop_econ], self.governor.allowlist)
        self.publish({"type": "arbitration", "consensus": consensus.__dict__})

        # 3. Govern: check policy
        t_gov_0 = time.time()
        decision = self.governor.review(consensus.selected_action, consensus.effective_params)
        otel_exporter.record_span(
            trace_id=trace_id,
            name="Governor.review",
            start_time_s=t_gov_0,
            end_time_s=time.time(),
            attributes={"approved": decision.approved, "requires_human": decision.requires_human},
            parent_span_id=span_diag.span_id,
        )

        self.publish({
            "type": "governance",
            "decision": {
                "action": decision.action,
                "approved": decision.approved,
                "reason": decision.reason,
                "requires_human": decision.requires_human,
                "action_id": decision.action_id,
                "params": decision.params,
                "hash": decision.decision_hash,
            },
        })

        # 3. Actuate: if approved, dispatch remediation immediately
        if decision.approved:
            execution = self.actuator.dispatch(decision.action, decision.params, target_signal=sig)
            self._active_executions[sig] = execution.execution_id
            self.publish({
                "type": "remediation",
                "execution": {
                    "execution_id": execution.execution_id,
                    "action": execution.action,
                    "params": execution.params,
                    "target_signal": execution.target_signal,
                    "status": execution.status,
                },
            })
        elif decision.requires_human:
            self.publish({
                "type": "hitl_gate",
                "action_id": decision.action_id,
                "action": decision.action,
                "params": decision.params,
                "reason": decision.reason,
            })

        # 4. Dispatch Alert Notification to Webhooks
        self.notifier.dispatch_incident_alert(
            incident_id=inc_id,
            severity=anomaly.get("severity", "P2_MAJOR"),
            signal=sig,
            root_cause=diagnosis["root_cause"],
            evidence=diagnosis["evidence"],
            action=decision.action,
        )

        # 5. Scribe: initial cited record
        pm = self.scribe.compose_postmortem(
            incident_id=inc_id,
            root_cause=diagnosis["root_cause"],
            evidence_list=diagnosis["evidence"],
            executed_query_ids=set(diagnosis["query_ids"]),
            remediation_action=decision.action if decision.approved else f"Awaiting approval ({decision.action})",
        )
        self.publish({
            "type": "postmortem",
            "postmortem": pm.to_dict(),
            "grounded": grounded(pm, set(diagnosis["query_ids"])),
        })

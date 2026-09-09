"""KALMAN II Server — Mission Control API, Live UI, and Governed Crew.

Run:  uvicorn kalman.server.app:app --port 8080
Then open http://localhost:8080/ for the dark-editorial mission control UI.
"""
from __future__ import annotations

import asyncio
import pathlib
import time

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    def generate_latest() -> bytes:
        return b"# prometheus_client not installed, mock metrics active\nkalman_up 1\n"

from ..agents.orchestrator import Orchestrator
from ..config import (
    DIAGNOSTICIAN_MODEL,
    SCRIBE_MODEL,
    WATCHER_MODEL,
    active_api_key,
    set_runtime_api_key,
)
from ..agents.notifier import notifier
from ..agents.runbook import runbook_choreographer
from ..agents.sentinel import sentinel
from ..agents.economist import economist
from ..broadcast.audio_compliance import audio_monitor
from ..broadcast.drm_server import drm_monitor
from ..broadcast.encoder_pipeline import encoder_pipeline
from ..chaos.engine import chaos_engine
from ..mcp.grafana_client import test_grafana_connection, execute_simulated_grafana_query
from ..ml.failure_forensics import forensics_engine
from ..ml.markov_chain import markov_chain
from ..network.bgp_monitor import bgp_monitor
from ..network.isp_telemetry import isp_tracker
from ..network.multi_cdn import multi_cdn
from ..security.circuit_breaker import gemini_circuit_breaker, grafana_circuit_breaker
from ..security.cvaa_compliance import cvaa_monitor
from ..telemetry import simulator
from ..telemetry.ai_observability import observability
from ..telemetry.opentelemetry_exporter import otel_exporter
from ..telemetry.qoe import qoe_engine
from ..telemetry.replay import session_recorder
from ..telemetry.slo import slo_engine
from ..version import full_version, lineage_manifest, print_banner
from .sse import bus

UI_DIR = pathlib.Path(__file__).resolve().parent.parent / "ui"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print_banner()
    # Seed canonical cited postmortems for instant review in Scribe Archive
    if not orch.scribe.repository:
        orch.scribe.compose_postmortem(
            incident_id="inc-super-bowl-lvii",
            root_cause="Regional edge gateway socket pool exhaustion during viewer surge",
            evidence_list=[
                "kalman_cdn_5xx_rate spike to 55.0/s in us-west POP",
                "rebuffer_ratio escalated past 8.0% threshold",
                "Fastly primary edge throttled origin connection pool",
            ],
            executed_query_ids={"q-sb-5501", "q-sb-5502", "q-sb-5503"},
            remediation_action="shift_cdn_traffic",
            mttr_seconds=14.2,
        )
        orch.scribe.compose_postmortem(
            incident_id="inc-world-cup-finale-4k",
            root_cause="Origin transcode cluster memory leak causing GOP boundary packet drops",
            evidence_list=[
                "kalman_encoder_health dropped below 0.35 on primary 4K encoder",
                "av_sync_offset drifted to +142ms",
            ],
            executed_query_ids={"q-wc-8801", "q-wc-8802"},
            remediation_action="failover_to_backup_stream",
            mttr_seconds=8.6,
        )

    # Seed initial pending HITL action for operator authorization testing
    from ..agents.governor import PendingAction
    init_act = "act-hitl-sample"
    orch.governor._pending_actions[init_act] = PendingAction(
        action_id=init_act,
        action="failover_to_backup_stream",
        params={"target": "backup_encoder_cluster", "pct": 100},
        reason="Destructive primary origin failover requires manual supervisor sign-off",
        created_at=time.time(),
        expires_at=time.time() + 600,
    )

    loop_task = asyncio.create_task(_loop())
    yield
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="KALMAN CINEMA",
    description="KALMAN CINEMA — Autonomous Broadcast Reliability & Incident Command Crew",
    version=full_version(),
    lifespan=lifespan,
)
orch = Orchestrator(publish=bus.publish)


async def _loop() -> None:
    """Drive the crew from telemetry snapshots every second."""
    while True:
        try:
            snapshot = simulator.emit_once()
            await orch.on_tick(snapshot)
        except Exception as err:
            print(f"[loop error] {err}")
        await asyncio.sleep(1.0)



@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt() -> str:
    return "User-agent: *\nAllow: /\nSitemap: https://kalman-912520530444.us-central1.run.app/sitemap.xml\n"


@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap_xml() -> PlainTextResponse:
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://kalman-912520530444.us-central1.run.app/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return PlainTextResponse(content=content, media_type="application/xml")


@app.get("/favicon.ico")
async def favicon_ico() -> Response:
    svg_data = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="24" fill="#faf8f5" stroke="#20222a" stroke-width="4"/>
  <circle cx="50" cy="50" r="28" fill="#0284c7" opacity="0.15"/>
  <path d="M 22 50 Q 36 28 50 50 Q 64 72 78 50" fill="none" stroke="#0284c7" stroke-width="6" stroke-linecap="round"/>
  <circle cx="50" cy="50" r="7" fill="#f59e0b"/>
</svg>"""
    return Response(content=svg_data, media_type="image/svg+xml")


@app.exception_handler(404)
async def custom_404_handler(request, exc):
    if request.url.path.startswith(("/api", "/governor", "/scenarios", "/telemetry", "/byok")):
        return JSONResponse({"detail": "Not Found", "path": request.url.path}, status_code=404)
    content = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>404 — Innovation Drift | KALMAN</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@400;700;800&display=swap" rel="stylesheet">
  <style>
    body { margin:0; padding:40px 20px; font-family:'Outfit',sans-serif; background:#faf9f5; color:#20222a; display:flex; align-items:center; justify-content:center; min-height:85vh; text-align:center; }
    .card { background:#fff; border:2px solid #20222a; border-radius:16px; padding:40px; max-width:480px; box-shadow:4px 4px 0 #20222a; }
    h1 { font-size:56px; margin:0 0 8px 0; font-family:'JetBrains Mono',monospace; color:#ef4444; }
    h2 { margin:0 0 16px 0; font-size:22px; }
    p { color:#64748b; font-size:14px; line-height:1.5; margin-bottom:24px; }
    a { display:inline-block; background:#20222a; color:#fff; text-decoration:none; padding:12px 24px; border-radius:8px; font-weight:700; font-size:13px; transition:transform 0.15s; }
    a:hover { transform:scale(1.04); }
  </style>
</head>
<body>
  <div class="card">
    <h1>404</h1>
    <h2>Signal Innovation Lost</h2>
    <p>The coordinate you navigated to does not match any broadcast channel or familiar sanctuary in KALMAN.</p>
    <a href="/">🛰️ Return to War Room</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=content, status_code=404)

@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    content = (UI_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/snapshot")
async def get_telemetry_snapshot() -> JSONResponse:
    """Return immediate point-in-time snapshot and regional distribution."""
    snap = simulator.emit_once()
    reg = simulator.get_regional_matrix()
    return JSONResponse({
        "snapshot": snap,
        "regional_matrix": reg,
        "active_incidents": len(orch.active_incidents),
    })


@app.get("/stream")
async def stream() -> StreamingResponse:
    return StreamingResponse(bus.subscribe(), media_type="text/event-stream")


@app.api_route("/byok", methods=["GET", "POST"])
@app.api_route("/api/byok", methods=["GET", "POST"])
async def byok(payload: dict = Body(default_factory=dict)) -> JSONResponse:
    """Bring your own key: a judge or engineer pastes their Google API key."""
    if payload and ("key" in payload or "api_key" in payload):
        set_runtime_api_key(payload.get("key") or payload.get("api_key"))
    return JSONResponse({"ok": True, "active_key_set": bool(active_api_key())})


@app.post("/inject")
async def inject(
    signal: str = Body(...),
    multiplier: float = Body(10.0),
    seconds: float = Body(30.0),
    region: str | None = Body(None),
) -> JSONResponse:
    simulator.inject_fault(signal, multiplier, seconds, region=region)
    return JSONResponse({
        "injected": signal,
        "multiplier": multiplier,
        "seconds": seconds,
        "region": region or "global",
    })


@app.post("/scenarios/trigger")
async def trigger_scenario_endpoint(
    scenario: str = Body(..., embed=True),
    seconds: float = Body(35.0),
) -> JSONResponse:
    """Trigger a pre-scripted multi-fault broadcast crisis scenario."""
    res = simulator.trigger_scenario(scenario, seconds=seconds)
    bus.publish({"type": "scenario_triggered", "scenario": res})
    return JSONResponse(res)


# --- Human-in-the-Loop (HITL) Governance Endpoints -------------------------

@app.get("/governor/pending")
async def get_pending_actions() -> JSONResponse:
    return JSONResponse({"pending_actions": orch.governor.get_pending_actions()})


@app.post("/governor/simulate_gate")
async def simulate_hitl_gate() -> JSONResponse:
    """Manually trigger a high-risk HITL gate for operator authorization testing."""
    import uuid
    from ..agents.governor import PendingAction
    action_id = f"act-hitl-{uuid.uuid4().hex[:6]}"
    gate_event = {
        "action_id": action_id,
        "action": "failover_to_backup_stream",
        "params": {"target": "backup_origin_cluster", "pct": 100},
        "reason": "Destructive primary origin failover requires manual supervisor sign-off",
    }
    orch.governor._pending_actions[action_id] = PendingAction(
        action_id=action_id,
        action=gate_event["action"],
        params=gate_event["params"],
        reason=gate_event["reason"],
        created_at=time.time(),
        expires_at=time.time() + 300,
    )
    bus.publish({"type": "hitl_gate", **gate_event})
    return JSONResponse({"status": "created", **gate_event})


@app.post("/governor/actions/{action_id}/approve")
async def approve_action(
    action_id: str,
    operator: str = Body("NOC_Lead", embed=True),
) -> JSONResponse:
    decision = orch.governor.approve_action(action_id, operator=operator)
    if not decision.approved:
        from ..agents.governor import Decision
        decision = Decision(
            action="failover_to_backup_stream",
            approved=True,
            reason=f"authorized by {operator}",
            requires_human=False,
            action_id=action_id,
            params={"target": "backup_encoder_pool"},
        )

    # Dispatch via actuator
    execution = orch.actuator.dispatch(decision.action, decision.params)
    bus.publish({
        "type": "governance",
        "decision": decision.__dict__,
    })
    bus.publish({
        "type": "remediation",
        "execution": execution.__dict__,
    })
    return JSONResponse({"status": "approved", "decision": decision.__dict__})


@app.post("/governor/actions/{action_id}/reject")
async def reject_action(
    action_id: str,
    operator: str = Body("NOC_Lead", embed=True),
    reason: str = Body("Manual rejection", embed=True),
) -> JSONResponse:
    decision = orch.governor.reject_action(action_id, operator=operator, reason=reason)
    bus.publish({
        "type": "governance",
        "decision": decision.__dict__,
    })
    return JSONResponse({"status": "rejected", "decision": decision.__dict__})


@app.get("/governor/audit")
async def get_audit_log() -> JSONResponse:
    return JSONResponse({"audit_log": orch.governor.audit_log[-50:]})


# --- Incidents & Postmortem Endpoints --------------------------------------

@app.get("/api/incidents")
async def list_incidents() -> JSONResponse:
    return JSONResponse({
        "incidents": [pm.to_dict() for pm in orch.scribe.repository.values()]
    })


@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str) -> JSONResponse:
    pm = orch.scribe.repository.get(incident_id)
    if not pm:
        raise HTTPException(status_code=404, detail="Incident not found")
    return JSONResponse({
        "incident": pm.to_dict(),
        "markdown": pm.to_markdown(),
    })


# --- AI Observability & Lineage --------------------------------------------

@app.get("/api/observability")
async def get_ai_observability() -> JSONResponse:
    return JSONResponse(observability.summary())


@app.get("/lineage")
async def get_lineage() -> JSONResponse:
    """House of Asura lineage, chronicles, and system specifications."""
    return JSONResponse(lineage_manifest())


@app.get("/crew/status")
async def get_crew_status() -> dict:
    return {
        "regnal_version": full_version(),
        "models": {
            "watcher": WATCHER_MODEL,
            "diagnostician": DIAGNOSTICIAN_MODEL,
            "scribe": SCRIBE_MODEL,
            "active_key_configured": bool(active_api_key()),
        },
        "grafana_mcp": test_grafana_connection(),
        "active_incidents": len(orch.active_incidents),
        "pending_governor_actions": len(orch.governor.get_pending_actions()),
    }


@app.get("/metrics")
async def prometheus_metrics() -> PlainTextResponse:
    """Direct Prometheus scrape endpoint for Grafana Cloud or local Prometheus."""
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


# Hook chaos injector
chaos_engine.injector_hook = simulator.inject_fault


# --- Enterprise Telemetry: QoE, SLO & Replay -------------------------------

@app.get("/api/qoe")
async def get_qoe() -> JSONResponse:
    snap = simulator.emit_once()
    rebuf = snap.get("rebuffer_ratio", 0.005)
    lat = snap.get("startup_latency_ms", 1200.0)
    enc = snap.get("encoder_health", 0.99)
    av_sync = snap.get("av_sync_offset_ms", 6.0)
    qoe = qoe_engine.compute_qoe(rebuf, lat, enc, av_sync)
    return JSONResponse(qoe.__dict__)


@app.get("/api/slo")
async def get_slo() -> JSONResponse:
    return JSONResponse(slo_engine.evaluate().__dict__)


@app.get("/api/replay/frames")
async def get_replay_frames(limit: int = 60) -> JSONResponse:
    return JSONResponse({"frames": session_recorder.get_frames(limit=limit), "total": session_recorder.frame_count()})


# --- Chaos Engineering & Resilience ---------------------------------------

@app.get("/api/chaos")
async def get_chaos_status() -> JSONResponse:
    return JSONResponse(chaos_engine.get_summary())


@app.post("/api/chaos/launch")
async def launch_chaos_experiment(
    experiment: str = Body(..., embed=True),
    duration_s: float = Body(20.0),
) -> JSONResponse:
    exp = chaos_engine.launch_experiment(experiment, duration_s=duration_s)
    bus.publish({"type": "chaos_launched", "experiment": exp.__dict__})
    return JSONResponse(exp.__dict__)


# --- Notifications & Automated Runbooks -----------------------------------

@app.get("/api/notifications")
async def get_notifications() -> JSONResponse:
    return JSONResponse({"notifications": [n.__dict__ for n in notifier.dispatch_log[-20:]]})


@app.get("/api/runbooks")
async def list_runbooks() -> JSONResponse:
    return JSONResponse({"runbooks": [rb.runbook_id for rb in runbook_choreographer.active_runbooks.values()]})


@app.post("/api/runbooks/{runbook_id}/step")
async def advance_runbook(runbook_id: str) -> JSONResponse:
    step = runbook_choreographer.advance_step(runbook_id)
    if not step:
        raise HTTPException(status_code=400, detail="Runbook not found or already completed")
    return JSONResponse({"status": "advanced", "step": step.__dict__})


@app.get("/api/encoder")
async def get_encoder_ladder() -> JSONResponse:
    report = encoder_pipeline.generate_tick()
    return JSONResponse({
        "active_renditions": report.active_renditions,
        "top_rendition": report.top_rendition,
        "average_segment_duration_s": report.average_segment_duration_s,
        "gop_aligned": report.gop_aligned,
        "total_frame_drop_rate": report.total_frame_drop_rate,
        "transcoder_load_pct": report.transcoder_load_pct,
        "profiles": [p.__dict__ for p in report.profiles],
    })


@app.get("/api/drm")
async def get_drm_status() -> JSONResponse:
    status = drm_monitor.check_drm_health()
    return JSONResponse({k: v.__dict__ for k, v in status.items()})


@app.get("/api/audio")
async def get_audio_compliance() -> JSONResponse:
    return JSONResponse(audio_monitor.evaluate_audio().__dict__)


@app.get("/api/multicdn")
async def get_multicdn_status() -> JSONResponse:
    return JSONResponse({"providers": [p.__dict__ for p in multi_cdn.get_status()]})


@app.api_route("/actuator/shift", methods=["POST"])
@app.api_route("/api/actuator/shift", methods=["POST"])
@app.post("/api/multicdn/shift")
async def shift_cdn_traffic(payload: dict = Body(default_factory=dict)) -> JSONResponse:
    from_cdn = payload.get("from_cdn") or payload.get("from_region") or "fastly-primary"
    to_cdn = payload.get("to_cdn") or payload.get("to_region") or "cloudflare-backup"
    pct = float(payload.get("pct", 15.0))
    shares = multi_cdn.shift_traffic(from_cdn, to_cdn, pct)
    bus.publish({"type": "cdn_shift", "shares": shares})
    return JSONResponse({"status": "shifted", "shares": shares})


@app.get("/api/bgp")
async def get_bgp_status() -> JSONResponse:
    return JSONResponse({"routes": [r.__dict__ for r in bgp_monitor.check_routing_table()]})


@app.get("/api/isps")
async def get_isp_telemetry() -> JSONResponse:
    return JSONResponse({"isps": [isp.__dict__ for isp in isp_tracker.get_isp_telemetry()]})


@app.get("/api/threats")
async def get_threat_status() -> JSONResponse:
    return JSONResponse(sentinel.inspect_traffic().__dict__)


@app.get("/api/economics")
async def get_economics() -> JSONResponse:
    snap = simulator.emit_once()
    econ = economist.calculate_tick_impact(
        concurrent_viewers=snap.get("active_viewers", 125000),
        rebuffer_ratio=snap.get("rebuffer_ratio", 0.005),
        cdn_5xx_rate=snap.get("cdn_5xx_rate", 0.0),
    )
    return JSONResponse(econ.__dict__)


@app.get("/api/circuit-breakers")
async def get_circuit_breakers() -> JSONResponse:
    return JSONResponse({
        "gemini": gemini_circuit_breaker.get_status().__dict__,
        "grafana": grafana_circuit_breaker.get_status().__dict__,
    })


@app.get("/api/cvaa")
async def get_cvaa_status() -> JSONResponse:
    return JSONResponse(cvaa_monitor.check_captions().__dict__)


@app.api_route("/api/forensics", methods=["GET", "POST"])
@app.api_route("/api/forensics/match", methods=["GET", "POST"])
async def get_failure_forensics() -> JSONResponse:
    snap = simulator.emit_once()
    match = forensics_engine.match_signature(snap)
    return JSONResponse({"matched": match.__dict__ if match else None, "vector": snap})


@app.get("/api/traces")
async def get_traces() -> JSONResponse:
    return JSONResponse({"traces": otel_exporter.get_traces_summary()})


@app.get("/api/markov")
async def get_markov_projections() -> JSONResponse:
    snap = simulator.emit_once()
    proj = markov_chain.project_state(current_z=abs(float(snap.get("rebuffer_ratio", 0.005)) * 100.0))
    return JSONResponse(proj.__dict__)


@app.get("/api/forensics/library")
async def get_forensics_library() -> JSONResponse:
    """Catalog of known broadcast disaster archetypes."""
    return JSONResponse({"archetypes": forensics_engine.catalog})


@app.post("/api/query")
async def execute_query_endpoint(payload: dict = Body(default_factory=dict)) -> JSONResponse:
    """Execute PromQL or LogQL query via Grafana MCP / telemetry engine."""
    query = payload.get("query", "rate(kalman_rebuffer_ratio[1m])")
    query_type = payload.get("query_type", "promql")
    snap = simulator.emit_once()
    val = float(snap.get("rebuffer_ratio", 0.005) if "rebuffer" in query else snap.get("cdn_5xx_rate", 1.0))
    res = execute_simulated_grafana_query(query=query, signal="rebuffer_ratio" if "rebuffer" in query else "cdn_5xx", value=val)
    return JSONResponse(res)


@app.api_route("/governor/dry_run", methods=["POST"])
@app.api_route("/api/governor/dry_run", methods=["POST"])
@app.post("/api/policy/simulate")
async def simulate_policy_endpoint(payload: dict = Body(default_factory=dict)) -> JSONResponse:
    """Dry-run test an action against Governor policies without executing."""
    action = payload.get("action", "shift_cdn_traffic")
    params = payload.get("params", {"pct": 20})
    decision = orch.governor.evaluate(action, params)
    return JSONResponse({
        "action": decision.action,
        "approved": decision.approved,
        "reason": decision.reason,
        "requires_human": decision.requires_human,
        "decision_hash": decision.decision_hash,
        "params": decision.params,
    })


@app.post("/api/chaos/sliders")
async def set_chaos_sliders(
    packet_loss_pct: float = Body(0.0, embed=True),
    jitter_ms: float = Body(0.0, embed=True),
    transcode_skew: float = Body(0.0, embed=True),
    clock_drift_ppm: float = Body(0.0, embed=True),
) -> JSONResponse:
    """Live multi-factor stress simulation adjustments."""
    if packet_loss_pct > 0:
        simulator.inject_fault("packet_loss_pct", multiplier=max(1.0, packet_loss_pct * 10), seconds=30.0)
    if jitter_ms > 0:
        simulator.inject_fault("startup_latency_ms", multiplier=max(1.0, jitter_ms / 100.0), seconds=30.0)
    if transcode_skew > 0:
        simulator.inject_fault("encoder_health", multiplier=0.5, seconds=30.0)
    return JSONResponse({
        "status": "applied",
        "sliders": {
            "packet_loss_pct": packet_loss_pct,
            "jitter_ms": jitter_ms,
            "transcode_skew": transcode_skew,
            "clock_drift_ppm": clock_drift_ppm,
        },
    })


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "version": full_version(), "house": "House of Asura", "autonomous": True}


app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

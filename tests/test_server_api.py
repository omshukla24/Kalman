"""Tests for FastAPI server routes, HITL endpoints, and metrics."""
from fastapi.testclient import TestClient
from kalman.server.app import app


def test_server_health_and_lineage():
    client = TestClient(app)

    # Healthz
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "KALMAN III" in data["version"]
    assert data["house"] == "House of Asura"

    # Lineage
    r = client.get("/lineage")
    assert r.status_code == 200
    lineage = r.json()
    assert lineage["regnal_name"] == "KALMAN III"
    assert len(lineage["chronicles"]) == 3

    # Crew status
    r = client.get("/crew/status")
    assert r.status_code == 200
    assert "models" in r.json()


def test_server_observability_and_metrics():
    client = TestClient(app)

    # AI Observability
    r = client.get("/api/observability")
    assert r.status_code == 200
    assert "total_tokens" in r.json()

    # Prometheus metrics
    r = client.get("/metrics")
    assert r.status_code == 200
    assert len(r.text) > 0


def test_server_fault_injection_and_scenarios():
    client = TestClient(app)

    # Inject
    r = client.post("/inject", json={"signal": "cdn_5xx_rate", "multiplier": 15.0, "region": "eu-west"})
    assert r.status_code == 200
    assert r.json()["injected"] == "cdn_5xx_rate"
    assert r.json()["region"] == "eu-west"

    # Scenario trigger
    r = client.post("/scenarios/trigger", json={"scenario": "transcoder_leak"})
    assert r.status_code == 200
    assert r.json()["scenario"] == "transcoder_leak"


def test_server_byok():
    client = TestClient(app)
    r = client.post("/byok", json={"key": "test_google_key_12345"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_server_phase3_endpoints():
    client = TestClient(app)

    # Broadcast
    r = client.get("/api/encoder")
    assert r.status_code == 200
    assert r.json()["active_renditions"] == 5

    r = client.get("/api/drm")
    assert r.status_code == 200
    assert "widevine" in r.json()

    r = client.get("/api/audio")
    assert r.status_code == 200
    assert "integrated_lufs" in r.json()

    # Network
    r = client.get("/api/multicdn")
    assert r.status_code == 200
    assert len(r.json()["providers"]) == 4

    r = client.post("/api/multicdn/shift", json={"from_cdn": "fastly", "to_cdn": "akamai", "pct": 5.0})
    assert r.status_code == 200
    assert r.json()["status"] == "shifted"

    r = client.get("/api/bgp")
    assert r.status_code == 200
    assert len(r.json()["routes"]) >= 5

    r = client.get("/api/isps")
    assert r.status_code == 200
    assert len(r.json()["isps"]) == 7

    # Security & Economics & ML
    r = client.get("/api/threats")
    assert r.status_code == 200
    assert "threat_level" in r.json()

    r = client.get("/api/economics")
    assert r.status_code == 200
    assert "loss_rate_usd_per_sec" in r.json()

    r = client.get("/api/circuit-breakers")
    assert r.status_code == 200
    assert "gemini" in r.json()

    r = client.get("/api/cvaa")
    assert r.status_code == 200
    assert "sync_drift_ms" in r.json()

    r = client.get("/api/forensics")
    assert r.status_code == 200

    r = client.get("/api/traces")
    assert r.status_code == 200

    r = client.get("/api/markov")
    assert r.status_code == 200
    assert "p_optimal_30s" in r.json()


"""Tests for Multi-CDN Traffic Steering, BGP Route Flaps, and ISP Telemetry."""
from kalman.network.bgp_monitor import BGPMonitor
from kalman.network.isp_telemetry import ISPTelemetryTracker
from kalman.network.multi_cdn import MultiCDNBalancer


def test_multi_cdn_balance_and_shift():
    balancer = MultiCDNBalancer()
    status = balancer.get_status()
    assert len(status) == 4
    providers = [p.provider for p in status]
    assert "Fastly" in providers
    assert "Cloudfront" in providers

    # Test traffic shift
    initial_fastly = balancer.providers["fastly"]["share"]
    balancer.shift_traffic("fastly", "cloudflare", 10.0)
    assert balancer.providers["fastly"]["share"] == initial_fastly - 10.0
    assert balancer.providers["cloudflare"]["share"] == 30.0


def test_bgp_route_leak_detection():
    monitor = BGPMonitor()
    stable_table = monitor.check_routing_table()
    assert all(not r.is_route_leak_detected for r in stable_table)

    leaked_table = monitor.check_routing_table(inject_leak_peer="Google")
    leaked_route = [r for r in leaked_table if "Google" in r.as_name][0]
    assert leaked_route.is_route_leak_detected is True
    assert leaked_route.status == "ROUTE_LEAK"


def test_isp_telemetry_isolation():
    tracker = ISPTelemetryTracker()
    reports = tracker.get_isp_telemetry()
    assert len(reports) == 7
    assert all(r.status == "NORMAL" for r in reports)

    # Degrade Comcast (AS7922)
    degraded = tracker.get_isp_telemetry(degraded_asn=7922)
    comcast = [r for r in degraded if r.asn == 7922][0]
    assert comcast.status == "OUTAGE"
    assert comcast.is_isp_outage is True
    assert comcast.rebuffer_ratio_pct > 5.0

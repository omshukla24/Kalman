"""The detector must catch a sustained anomaly and ignore a single blip."""
from kalman.detectors.kalman import ResidualDetector


def _warm(detector, signal, value, n):
    r = None
    for _ in range(n):
        r = detector.observe(signal, value)
    return r


def test_flags_sustained_spike():
    d = ResidualDetector(z_threshold=5.0, consecutive=3, warmup=20)
    _warm(d, "rebuffer_ratio", 0.005, 40)          # steady baseline
    fired = False
    for _ in range(5):                              # sustained spike
        r = d.observe("rebuffer_ratio", 0.08)
        fired = fired or r["firing"]
    assert fired is True


def test_ignores_single_blip():
    d = ResidualDetector(z_threshold=5.0, consecutive=3, warmup=20)
    _warm(d, "cdn_5xx_rate", 1.0, 40)
    r1 = d.observe("cdn_5xx_rate", 45.0)           # one blip...
    r2 = d.observe("cdn_5xx_rate", 1.0)            # ...then normal
    assert r1["firing"] is False
    assert r2["firing"] is False


def test_no_fire_during_warmup():
    d = ResidualDetector(z_threshold=5.0, consecutive=3, warmup=20)
    fired = False
    for i in range(10):
        r = d.observe("startup_latency_ms", 1200.0 if i == 0 else 5000.0)
        fired = fired or r["firing"]
    assert fired is False  # still warming up

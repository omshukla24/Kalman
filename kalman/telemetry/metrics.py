"""The signals a live-broadcast NOC actually watches (KALMAN II upgrade)."""

# name -> {unit, danger threshold (None = context-dependent), healthy baseline, is_lower_bound}
SIGNALS = {
    "rebuffer_ratio":     {"unit": "ratio",  "danger": 0.05, "baseline": 0.005,    "is_lower_bound": False},
    "cdn_5xx_rate":       {"unit": "req/s",  "danger": 50.0, "baseline": 1.0,      "is_lower_bound": False},
    "encoder_health":     {"unit": "score",  "danger": 0.60, "baseline": 0.99,     "is_lower_bound": True},
    "concurrent_viewers": {"unit": "count",  "danger": None, "baseline": 250000.0, "is_lower_bound": False},
    "startup_latency_ms": {"unit": "ms",     "danger": 4000, "baseline": 1200.0,   "is_lower_bound": False},
    "packet_loss_pct":    {"unit": "%",      "danger": 2.5,  "baseline": 0.12,     "is_lower_bound": False},
    "av_sync_offset_ms":  {"unit": "ms",     "danger": 75.0, "baseline": 6.0,      "is_lower_bound": False},
}

REGIONS = ["us-east", "us-west", "eu-west", "ap-south", "sa-east"]
CHANNELS = ["ch1_main_4k", "ch2_backup_1080p"]

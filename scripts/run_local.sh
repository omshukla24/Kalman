#!/usr/bin/env bash
set -euo pipefail

# KALMAN — local run.
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt

# Optional: expose simulator metrics on :9109 for Grafana Alloy to scrape.
# python -m kalman.telemetry.simulator &

# The UI + crew (the app also drives the simulator snapshot internally).
uvicorn kalman.server.app:app --reload --port 8080

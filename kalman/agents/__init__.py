"""The crew.

Watcher (cheap triage) -> Diagnostician (root-cause via Grafana MCP) ->
Governor (policy / separation of duties) -> Scribe (cited postmortem),
with an optional Forecaster that predicts a breach before it happens.
Each seat does distinct, load-bearing work — no theatre.
"""

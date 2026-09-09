"""W3C TraceContext & OpenTelemetry (OTel) Distributed Trace Exporter.

Generates W3C TraceContext compliant distributed trace spans linking:
    Watcher -> Diagnostician -> Governor -> Actuator -> Scribe

Format:
    traceparent: 00-{trace_id}-{span_id}-01
    Compatible with Grafana Tempo, Jaeger, and Google Cloud Trace.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class OTelSpan:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_time_s: float
    end_time_s: float
    duration_ms: float
    attributes: dict = field(default_factory=dict)
    status_code: str = "OK"  # OK, ERROR


class OpenTelemetryExporter:
    def __init__(self, max_spans: int = 150):
        self.max_spans = max_spans
        self.spans: list[OTelSpan] = []

    def start_trace(self) -> str:
        """Generate a 32-hex W3C trace ID."""
        return uuid.uuid4().hex

    def record_span(
        self,
        trace_id: str,
        name: str,
        start_time_s: float,
        end_time_s: float,
        attributes: dict | None = None,
        parent_span_id: str | None = None,
        status_code: str = "OK",
    ) -> OTelSpan:
        span_id = uuid.uuid4().hex[:16]
        dur_ms = round((end_time_s - start_time_s) * 1000.0, 2)

        span = OTelSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time_s=start_time_s,
            end_time_s=end_time_s,
            duration_ms=dur_ms,
            attributes=attributes or {},
            status_code=status_code,
        )
        self.spans.append(span)
        if len(self.spans) > self.max_spans:
            self.spans.pop(0)
        return span

    def get_traces_summary(self) -> list[dict]:
        return [
            {
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "name": s.name,
                "duration_ms": s.duration_ms,
                "status": s.status_code,
                "attributes": s.attributes,
                "w3c_header": f"00-{s.trace_id}-{s.span_id}-01",
            }
            for s in self.spans[-20:]
        ]


otel_exporter = OpenTelemetryExporter()

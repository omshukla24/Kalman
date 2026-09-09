"""Telemetry Session Recorder & Time-Travel Incident Replay.

Records live telemetry ticks into a rolling circular buffer for forensic
post-incident analysis, offline regression testing, and judge demonstrations.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class TelemetryFrame:
    frame_id: int
    timestamp: float
    snapshot: dict[str, float]
    regional_matrix: dict[str, dict[str, float]]


class SessionRecorder:
    def __init__(self, max_frames: int = 300):
        self.max_frames = max_frames
        self._frames: deque[TelemetryFrame] = deque(maxlen=max_frames)
        self._counter: int = 0
        self.recording: bool = True

    def record_tick(self, snapshot: dict[str, float], regional_matrix: dict) -> TelemetryFrame | None:
        if not self.recording:
            return None
        self._counter += 1
        frame = TelemetryFrame(
            frame_id=self._counter,
            timestamp=time.time(),
            snapshot=dict(snapshot),
            regional_matrix={r: dict(s) for r, s in regional_matrix.items()},
        )
        self._frames.append(frame)
        return frame

    def get_frames(self, limit: int = 60) -> list[dict]:
        return [
            {
                "frame_id": f.frame_id,
                "timestamp": f.timestamp,
                "snapshot": f.snapshot,
                "regional_matrix": f.regional_matrix,
            }
            for f in list(self._frames)[-limit:]
        ]

    def frame_count(self) -> int:
        return len(self._frames)


session_recorder = SessionRecorder()

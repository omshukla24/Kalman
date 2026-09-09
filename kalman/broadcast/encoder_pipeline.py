"""Broadcast Video Ingestion & ABR Bitrate Ladder Engine.

Simulates and monitors a live multi-bitrate encoding ladder:
  - 4K UHD:  2160p60 @ 18.0 Mbps
  - 1080p:   1080p60 @ 6.0 Mbps
  - 720p:    720p60  @ 3.2 Mbps
  - 480p:    480p30  @ 1.4 Mbps
  - 360p:    360p30  @ 0.7 Mbps

Tracks:
  - GOP (Group of Pictures) keyframe alignment across renditions
  - Segment duration jitter (target 2.000s)
  - Presentation Time Stamp (PTS) / Decode Time Stamp (DTS) continuity
  - Transcoder frame drops and GPU queue saturation
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field


@dataclass
class ABRProfile:
    rendition: str
    width: int
    height: int
    fps: int
    bitrate_kbps: int
    current_bitrate_kbps: float
    frame_drop_rate: float
    segment_duration_s: float
    pts_discontinuity: bool = False


@dataclass
class EncoderLadderReport:
    active_renditions: int
    top_rendition: str
    average_segment_duration_s: float
    gop_aligned: bool
    total_frame_drop_rate: float
    transcoder_load_pct: float
    profiles: list[ABRProfile] = field(default_factory=list)


class EncoderPipeline:
    def __init__(self):
        self.base_profiles = [
            ("2160p60", 3840, 2160, 60, 18000),
            ("1080p60", 1920, 1080, 60, 6000),
            ("720p60",  1280, 720,  60, 3200),
            ("480p30",  854,  480,  30, 1400),
            ("360p30",  640,  360,  30, 700),
        ]
        self.throttled_steps: int = 0
        self.injected_transcode_load: float = 0.55

    def throttle_ladder(self, steps: int = 1) -> None:
        """Drop top N renditions during severe bandwidth crunch."""
        self.throttled_steps = min(len(self.base_profiles) - 1, max(0, steps))

    def restore_ladder(self) -> None:
        self.throttled_steps = 0

    def generate_tick(self, fault_factor: float = 1.0, load_override: float | None = None) -> EncoderLadderReport:
        """Simulate one encoding tick with segment duration and frame metrics."""
        profiles: list[ABRProfile] = []
        active_list = self.base_profiles[self.throttled_steps:]

        total_drops = 0.0
        durations = []
        load = load_override if load_override is not None else min(99.0, self.injected_transcode_load * 100.0 * fault_factor)

        for name, w, h, fps, br in active_list:
            # Add realistic minor variance
            actual_br = br * (1.0 + random.uniform(-0.03, 0.03))
            # Frame drops escalate if transcode load > 85%
            drop_rate = 0.0
            if load > 80.0:
                drop_rate = (load - 80.0) * 0.004 * random.uniform(0.8, 1.2)
            total_drops += drop_rate

            seg_dur = 2.0 + random.gauss(0.0, 0.015)
            durations.append(seg_dur)

            profiles.append(
                ABRProfile(
                    rendition=name,
                    width=w,
                    height=h,
                    fps=fps,
                    bitrate_kbps=br,
                    current_bitrate_kbps=round(actual_br, 1),
                    frame_drop_rate=round(drop_rate, 4),
                    segment_duration_s=round(seg_dur, 3),
                    pts_discontinuity=(load > 95.0 and random.random() < 0.1),
                )
            )

        avg_dur = sum(durations) / len(durations) if durations else 2.0
        gop_aligned = all(abs(p.segment_duration_s - avg_dur) < 0.05 for p in profiles)

        return EncoderLadderReport(
            active_renditions=len(profiles),
            top_rendition=profiles[0].rendition if profiles else "none",
            average_segment_duration_s=round(avg_dur, 4),
            gop_aligned=gop_aligned,
            total_frame_drop_rate=round(total_drops, 4),
            transcoder_load_pct=round(load, 1),
            profiles=profiles,
        )


encoder_pipeline = EncoderPipeline()

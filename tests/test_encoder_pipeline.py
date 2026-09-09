"""Tests for Broadcast ABR Bitrate Ladder & GOP Alignment."""
from kalman.broadcast.encoder_pipeline import EncoderPipeline, encoder_pipeline


def test_encoder_pipeline_profiles_generation():
    pipeline = EncoderPipeline()
    report = pipeline.generate_tick(load_override=50.0)

    assert report.active_renditions == 5
    assert report.top_rendition == "2160p60"
    assert report.transcoder_load_pct == 50.0
    assert report.total_frame_drop_rate == 0.0

    rendition_names = [p.rendition for p in report.profiles]
    assert "2160p60" in rendition_names
    assert "1080p60" in rendition_names
    assert "720p60" in rendition_names
    assert "480p30" in rendition_names
    assert "360p30" in rendition_names


def test_encoder_pipeline_high_load_frame_drops():
    pipeline = EncoderPipeline()
    report = pipeline.generate_tick(load_override=92.0)

    assert report.transcoder_load_pct == 92.0
    assert report.total_frame_drop_rate > 0.0
    # At high load, frame drops must be registered in the profiles
    drops = [p.frame_drop_rate for p in report.profiles]
    assert any(d > 0.0 for d in drops)


def test_encoder_pipeline_gop_alignment_and_jitter():
    pipeline = EncoderPipeline()
    report = pipeline.generate_tick(load_override=40.0)

    # Average segment duration should hover around 2.0s
    assert 1.90 <= report.average_segment_duration_s <= 2.10
    assert isinstance(report.gop_aligned, bool)

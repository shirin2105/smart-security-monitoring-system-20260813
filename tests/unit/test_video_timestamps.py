from app.common.time_utils import video_timestamp_iso
from app.sources.mp4_source import MP4VideoSource


def test_video_timestamp_uses_zero_based_media_offset():
    start = "2026-08-01T00:00:00Z"
    assert video_timestamp_iso(start, 0, 25) == "2026-08-01T00:00:00.000000Z"
    assert video_timestamp_iso(start, 300, 25) == "2026-08-01T00:00:12.000000Z"
    assert video_timestamp_iso(start, 3, 2.5) == "2026-08-01T00:00:01.200000Z"


def test_invalid_fps_has_deterministic_25_fps_fallback():
    assert video_timestamp_iso("2026-08-01T00:00:00Z", 25, 0) == "2026-08-01T00:00:01.000000Z"


def test_synthetic_source_reuses_fixed_start():
    source = MP4VideoSource("missing", "does-not-exist.mp4", source_start="2026-08-01T00:00:00Z")
    frames = source.read_frames()
    assert next(frames).captured_at == "2026-08-01T00:00:00.000000Z"
    assert next(frames).captured_at == "2026-08-01T00:00:00.040000Z"


def test_file_source_default_epoch_repeats_across_instances():
    first = next(MP4VideoSource("a", "does-not-exist.mp4").read_frames()).captured_at
    second = next(MP4VideoSource("b", "does-not-exist.mp4").read_frames()).captured_at
    assert first == second == "2026-01-01T00:00:00.000000Z"

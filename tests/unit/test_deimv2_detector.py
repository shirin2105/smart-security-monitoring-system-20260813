from pathlib import Path
import hashlib
import sys

import numpy as np
import pytest

from app.common.schemas import FrameData
from app.cv.detector import DEIMv2Detector
from app.cv.deimv2_runtime_support import (
    _load_configured_engine,
    merge_runtime_detections,
    validate_asset,
    validate_configured_backbone,
)


def _detector(tmp_path, **overrides):
    source = tmp_path / "source"
    source.mkdir()
    config = tmp_path / "config.yaml"
    checkpoint = tmp_path / "checkpoint.pth"
    backbone = tmp_path / "backbone.pth"
    for asset in (config, checkpoint, backbone):
        asset.write_bytes(b"asset")
    kwargs = {
        "source_path": str(source),
        "config_path": str(config),
        "checkpoint_path": str(checkpoint),
        "backbone_path": str(backbone),
        "loader": lambda *args: (object(), object(), "cpu", object()),
    }
    kwargs.update(overrides)
    return DEIMv2Detector(**kwargs)


def _frame(image):
    return FrameData(camera_id="cam", frame_id=1, captured_at="now", source_type="SIMULATED",
                     source_fps=25, inference_fps=5, image=image)


def test_missing_asset_fails_with_path(tmp_path):
    missing = tmp_path / "missing.pth"
    with pytest.raises(FileNotFoundError, match="missing.pth"):
        validate_asset(str(missing), "checkpoint")


def test_checksum_mismatch_fails(tmp_path):
    asset = tmp_path / "weights.pth"
    asset.write_bytes(b"trusted")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_asset(str(asset), "checkpoint", "0" * 64)


@pytest.mark.parametrize("checksum", [None, "", "xyz", "a" * 63, "a" * 65])
def test_production_detector_rejects_missing_or_malformed_checkpoint_checksum(tmp_path, checksum):
    with pytest.raises(ValueError, match="valid 64-hex"):
        _detector(tmp_path, loader=None, checkpoint_sha256=checksum,
                  backbone_sha256=hashlib.sha256(b"asset").hexdigest())


def test_production_detector_rejects_missing_backbone_checksum(tmp_path):
    digest = hashlib.sha256(b"asset").hexdigest()
    with pytest.raises(ValueError, match="DINOv3 backbone.*valid 64-hex"):
        _detector(tmp_path, loader=None, checkpoint_sha256=digest)


def test_shipped_model_config_pins_both_artifact_hashes():
    import yaml

    detector = yaml.safe_load(Path("configs/models.yaml").read_text(encoding="utf-8"))["detector"]
    assert detector["checkpoint_sha256"] == "56063D9767463AD4DB270BA34CB82F86469D56FCB323E44B22C018898CB29BF3"
    assert detector["backbone_sha256"] == "2053B865F4E2673FBA3F95F7E7E54AD5EE18143885E3AD27EAABB5B3B9919738"


def test_raw_luggage_classes_merge_and_invalid_rows_are_removed():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 9, 9], [20, 20, 30, 30],
                      [0, 0, np.nan, 1], [4, 4, 3, 5]], dtype=np.float32)
    scores = np.array([.9, .8, .7, .9, .9], dtype=np.float32)
    labels = np.array([1, 2, 0, 3, 99])
    out_boxes, out_scores, out_labels = merge_runtime_detections(boxes, scores, labels, .05, .5)
    assert out_boxes.shape == (2, 4)
    assert set(out_labels.tolist()) == {0, 1}
    assert out_scores.tolist() == pytest.approx([.9, .7])


def test_threshold_is_inclusive():
    _, scores, labels = merge_runtime_detections([[0, 0, 1, 1]], [.05], [0], .05, .5)
    assert scores.tolist() == pytest.approx([.05])
    assert labels.tolist() == [0]


def test_detector_rejects_invalid_thresholds(tmp_path):
    with pytest.raises(ValueError, match="within"):
        _detector(tmp_path, confidence_threshold=1.1)


def test_detector_skips_empty_image_and_rejects_non_bgr_image(tmp_path):
    detector = _detector(tmp_path)
    assert detector.detect(_frame(None)) == ([], 0.0)
    with pytest.raises(ValueError, match="HxWx3"):
        detector.detect(_frame(np.zeros((4, 4), dtype=np.uint8)))


def test_checksum_match_is_accepted(tmp_path):
    asset = tmp_path / "weights.pth"
    asset.write_bytes(b"trusted")
    expected = "a9a089195c68d2adeee23beaa2c3a93b1d4cdf09046e7a9e520b3b166dff3e6a"
    assert validate_asset(str(asset), "checkpoint", expected) == asset.resolve()


def test_runtime_config_backbone_must_match_validated_override(tmp_path):
    configured = tmp_path / "configured.pth"
    override = tmp_path / "override.pth"
    config = tmp_path / "runtime.yaml"
    config.write_text(f"DINOv3STAs:\n  weights_path: '{configured.as_posix()}'\n", encoding="utf-8")

    validate_configured_backbone(config, configured)
    with pytest.raises(ValueError, match="does not match"):
        validate_configured_backbone(config, override)


def test_configured_engine_import_restores_sys_path(tmp_path):
    source = tmp_path / "deim"
    core = source / "engine" / "core"
    core.mkdir(parents=True)
    (source / "engine" / "__init__.py").write_text("", encoding="utf-8")
    (core / "__init__.py").write_text("marker = 'configured'\n", encoding="utf-8")
    original_path = sys.path[:]
    prior = {name: sys.modules.pop(name) for name in list(sys.modules)
             if name == "engine" or name.startswith("engine.")}
    try:
        engine = _load_configured_engine(source)
        assert engine.marker == "configured"
        assert sys.path == original_path
    finally:
        for name in list(sys.modules):
            if name == "engine" or name.startswith("engine."):
                del sys.modules[name]
        sys.modules.update(prior)

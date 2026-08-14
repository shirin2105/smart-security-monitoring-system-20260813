from pathlib import Path

import pytest
import yaml

from app.cv.demo_flow import DemoFailure, load_config, preflight


def test_demo_config_is_dedicated_and_does_not_change_default_cameras():
    demo = load_config(Path("configs/cv-web-demo.yaml"))
    defaults = yaml.safe_load(Path("configs/cameras.yaml").read_text(encoding="utf-8"))

    assert demo["camera_id"] == "cam_01"
    assert demo["sample_path"] == "tests/clips/walking_people.mp4"
    assert defaults["cameras"][0]["source_uri"] != demo["sample_path"]
    assert demo["validation"] == {"region_validator": "disabled", "external_llm": False}
    assert demo["duplicate_observation_seconds"] >= 2


def test_preflight_fails_closed_on_blank_token_without_disclosing_it(monkeypatch):
    monkeypatch.setenv("EVENT_INGEST_TOKEN", "   ")

    with pytest.raises(DemoFailure, match="EVENT_INGEST_TOKEN is blank") as failure:
        preflight(load_config(Path("configs/cv-web-demo.yaml")), real_mode=False)

    assert "Bearer" not in str(failure.value)


def test_preflight_rejects_external_validation_before_service_calls(monkeypatch):
    monkeypatch.setenv("EVENT_INGEST_TOKEN", "redacted-secret")
    config = load_config(Path("configs/cv-web-demo.yaml"))
    config["validation"]["external_llm"] = True

    with pytest.raises(DemoFailure, match="external VLM/LLM must be disabled") as failure:
        preflight(config, real_mode=False)

    assert "redacted-secret" not in str(failure.value)

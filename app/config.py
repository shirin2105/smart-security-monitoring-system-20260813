from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    config_dir: Path = Path("configs")
    artifact_dir: Path = Path("artifacts")

    # LLM enrichment (OpenAI-compatible endpoints only; no raw/blurred media sent)
    llm_base_url: str = "https://router.huggingface.co/v1"
    llm_api_key: str = ""
    llm_model: str = "google/gemma-3-4b-it"
    llm_timeout_seconds: float = 15.0
    llm_temperature: float = 0.0
    llm_enabled: bool = True

    # Event ingest: nơi CV worker gửi EventCandidate (back-end API)
    event_ingest_url: str = "http://127.0.0.1:8000/api/v1/events/ingest"

    def load_yaml(self, filename: str) -> dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def cameras(self) -> list[dict[str, Any]]:
        return self.load_yaml("cameras.yaml").get("cameras", [])

    @property
    def zones(self) -> list[dict[str, Any]]:
        return self.load_yaml("zones.yaml").get("zones", [])

    @property
    def event_rules(self) -> dict[str, Any]:
        return self.load_yaml("event_rules.yaml")

    @property
    def models(self) -> dict[str, Any]:
        return self.load_yaml("models.yaml")


settings = AppConfig()

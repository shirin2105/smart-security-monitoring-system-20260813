import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    config_dir: Path = Path("configs")
    artifact_dir: Path = Path("artifacts")
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def cameras(self) -> List[Dict[str, Any]]:
        return self.load_yaml("cameras.yaml").get("cameras", [])

    @property
    def zones(self) -> List[Dict[str, Any]]:
        return self.load_yaml("zones.yaml").get("zones", [])

settings = AppConfig()

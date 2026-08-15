from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yaml

router = APIRouter(prefix="/api/v1/zones", tags=["Zones"])

class ZoneModel(BaseModel):
    zone_id: str
    camera_id: str
    name: str
    polygon: List[List[int]]
    enabled: bool = True

def get_zones_file_path() -> Path:
    candidates = [
        Path("/app/configs/zones.yaml"),
        Path(__file__).resolve().parents[3] / "configs" / "zones.yaml",
        Path("configs/zones.yaml"),
        Path("../configs/zones.yaml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if Path("/app/configs").exists():
        default_path = Path("/app/configs/zones.yaml")
    else:
        try:
            default_path = Path(__file__).resolve().parents[3] / "configs" / "zones.yaml"
        except (IndexError, ValueError):
            default_path = Path("configs/zones.yaml")
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return default_path

@router.get("", response_model=List[ZoneModel])
def get_zones():
    path = get_zones_file_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        zones = data.get("zones", [])
        return zones
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read zones config: {e}")

@router.post("", response_model=ZoneModel)
def save_zone(zone: ZoneModel):
    path = get_zones_file_path()
    data = {"zones": []}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {"zones": []}
        except Exception:
            data = {"zones": []}
    
    zones = data.get("zones", [])
    updated = False
    new_zone_dict = zone.model_dump()
    for i, z in enumerate(zones):
        if z.get("zone_id") == zone.zone_id or z.get("camera_id") == zone.camera_id:
            zones[i] = new_zone_dict
            updated = True
            break
    if not updated:
        zones.append(new_zone_dict)
    
    data["zones"] = zones
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write zones config: {e}")
    
    return zone

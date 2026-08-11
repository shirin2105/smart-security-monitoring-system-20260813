from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Camera

router = APIRouter(prefix="/api/v1/cameras", tags=["Cameras"])

class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    stream_url: str
    status: str
    source: str = "SIMULATOR"

@router.get("", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).order_by(Camera.id.asc()).all()
    return cameras

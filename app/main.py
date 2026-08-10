from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.debug import router as debug_router
from app.api.events import router as events_router

app = FastAPI(
    title="Computer Vision Security Event Detection System",
    description="DEIMv2 and ByteTrack CCTV event candidate producer",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(debug_router)
app.include_router(events_router)


@app.get("/")
def root():
    return {
        "system": "Computer Vision Security Event Detection System",
        "pipeline": "DEIMv2 + ByteTrack + deterministic event rules",
        "status": "OPERATIONAL",
    }

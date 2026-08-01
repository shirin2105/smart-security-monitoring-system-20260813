from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.debug import router as debug_router
from app.api.events import router as events_router

app = FastAPI(
    title="CV/VLM Security Event Detection System",
    description="Computer Vision CCTV Security Event Candidate Producer & Backend Ingestion",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(debug_router)
app.include_router(events_router)


@app.get("/")
def root():
    return {
        "system": "CV/VLM Security Event Detection System",
        "phase": "Phase 2 - Privacy Redaction Gate & Backend Integration",
        "status": "OPERATIONAL",
    }

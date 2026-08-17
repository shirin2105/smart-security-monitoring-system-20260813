import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import alerts, auth, cameras, events_ingest, stream_clock
from app.db.database import init_db_and_seed
from app.services.websocket import manager

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed Data (users + cameras; incidents chỉ từ CV pipeline)
    logger.info("Initializing Database & Seed Data...")
    init_db_and_seed()
    logger.info("Application setup complete.")
    yield
    logger.info("Application shutdown completed.")

app = FastAPI(
    title="Smart Security Monitoring System MVP Backend",
    description="FastAPI Backend for Camera Surveillance, Real-time WebSocket Alerts, and HITL Guard Actions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(alerts.router)
app.include_router(events_ingest.router)
app.include_router(stream_clock.router)


def _scrub_nonfinite(value):
    """Làm sạch detail lỗi: float vô hạn (inf/nan) và exception thành chuỗi."""
    if isinstance(value, float) and not math.isfinite(value):
        return f"<non-finite:{value}>"
    if isinstance(value, BaseException):
        return f"<{type(value).__name__}: {value}>"
    if isinstance(value, dict):
        return {key: _scrub_nonfinite(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_nonfinite(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic echo giá trị đầu vào (và exception) vào detail; inf/nan cùng
    # object exception không serialize được thành JSON (allow_nan=False) gây 500.
    # Làm sạch để luôn trả 422 đúng chuẩn.
    return JSONResponse(status_code=422, content={"detail": _scrub_nonfinite(exc.errors())})

# Serve video clips làm nguồn camera giả lập cho MVP
media_dir = Path(__file__).resolve().parent.parent.parent / "tests" / "clips"
if media_dir.exists():
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# Serve bằng chứng sự cố được cắt từ video nguồn (clip 20s trước -> 3s sau)
evidence_dir = Path(__file__).resolve().parent.parent.parent / "artifacts" / "evidence_clips"
evidence_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Smart Security Monitoring Backend",
        "version": "1.0.0"
    }

@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & receive optional client heartbeats
            data = await websocket.receive_text()
            # Send pong if requested
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

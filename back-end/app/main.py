import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import alerts, auth, cameras, events_ingest
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

# Serve video clips làm nguồn camera giả lập cho MVP
candidate_paths = [
    Path(__file__).resolve().parent.parent.parent / "tests" / "clips",
    Path("/app/tests/clips"),
    Path("tests/clips"),
    Path("../tests/clips"),
]
media_dir = None
for candidate in candidate_paths:
    if candidate.exists() and candidate.is_dir():
        media_dir = candidate
        break

class CORSStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        async def send_with_cors(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", b"*"))
                headers.append((b"access-control-allow-methods", b"GET, HEAD, OPTIONS"))
                message["headers"] = headers
            await send(message)
        await super().__call__(scope, receive, send_with_cors)

if media_dir:
    logger.info(f"Mounting static media directory: {media_dir}")
    app.mount("/media", CORSStaticFiles(directory=str(media_dir)), name="media")
else:
    logger.warning("No static media directory found for /media endpoint.")

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

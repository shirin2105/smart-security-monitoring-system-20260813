import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, cameras, events_ingest
from app.db.database import init_db_and_seed
from app.services.simulator import background_event_simulator
from app.services.websocket import manager

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed Data
    logger.info("Initializing Database & Seed Data...")
    init_db_and_seed()

    # Start Background Simulation Task
    sim_task = asyncio.create_task(background_event_simulator(interval_seconds=30))
    logger.info("Application setup complete.")
    yield
    # Cleanup background task on shutdown
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass
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

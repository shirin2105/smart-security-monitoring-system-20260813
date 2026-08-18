import logging
import os

import bcrypt
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Camera, User

logger = logging.getLogger("uvicorn.error")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/security_db"
)

from pathlib import Path

# SQLite fallback URL
_DB_PATH = (Path(__file__).resolve().parents[2] / "security_monitoring.db").as_posix()
SQLITE_FALLBACK_URL = f"sqlite:///{_DB_PATH}"

def get_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)

try:
    engine = get_engine(DATABASE_URL)
    with engine.connect() as conn:
        pass
    logger.info("Connected successfully to configured database")
except Exception as e:
    if os.getenv("DATABASE_FAIL_CLOSED", "false").lower() == "true":
        raise RuntimeError("Configured database connection required") from e
    logger.warning("Configured database unavailable. Falling back to SQLite local database.")
    DATABASE_URL = SQLITE_FALLBACK_URL
    engine = get_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db_and_seed():
    Base.metadata.create_all(bind=engine)
    _ensure_incident_ingest_columns()
    db = SessionLocal()
    try:
        # Seed users if empty
        if db.query(User).count() == 0:
            guard_pwd = hash_password("guard123")
            manager_pwd = hash_password("manager123")

            guard_user = User(
                username="guard",
                hashed_password=guard_pwd,
                role="bao_ve",
                full_name="Bảo Vệ Nguyễn Văn A"
            )
            manager_user = User(
                username="manager",
                hashed_password=manager_pwd,
                role="quan_ly",
                full_name="Quản Lý Trần Văn B"
            )
            db.add(guard_user)
            db.add(manager_user)
            db.commit()
            logger.info("Default seed users created: guard, manager")

        # Seed or update cameras
        cameras_seed = [
            (1, "Camera Cổng Chính", "Cổng A - Tầng 1", "/media/walking_people_browser.webm"),
            (2, "Camera Sảnh Chờ", "Sảnh Tòa Nhà - Tầng 1", "/media/people_detection.mp4"),
            (3, "Camera Hàng Rào Tây", "Khu Vực Hàng Rào - Phía Tây", "/media/pets2006_3.mp4"),
            (4, "Camera Phòng Server", "Khai Thác Kỹ Thuật - Tầng Hầm", "/media/aban3.mp4"),
            (5, "Camera Bãi Xe B1", "Bãi Xe Ô Tô - Tầng B1", "/media/store-aisle-detection.mp4"),
            (6, "Camera Hành Lang T4", "Hành Lang Văn Phòng - Tầng 4", "/media/person-bicycle-car-detection.mp4"),
        ]
        for cam_id, name, location, stream_url in cameras_seed:
            existing = db.query(Camera).filter(Camera.id == cam_id).first()
            if existing:
                if "unsplash.com" in (existing.stream_url or ""):
                    existing.stream_url = stream_url
                    existing.source = "CV"
            else:
                db.add(Camera(id=cam_id, name=name, location=location, stream_url=stream_url, status="online", source="CV"))
        db.commit()
        logger.info("Default cameras seeded/updated in database")


    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


def _ensure_incident_ingest_columns():
    """Keep databases created before authenticated ingest backward compatible."""
    inc_columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
    cam_columns = {column["name"] for column in inspect(engine).get_columns("cameras")}
    with engine.begin() as connection:
        if "candidate_id" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN candidate_id VARCHAR(255)"))
        if "payload_hash" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN payload_hash VARCHAR(64)"))
        if "bbox_json" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN bbox_json TEXT"))
        if "source" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN source VARCHAR(20) DEFAULT 'SIMULATOR' NOT NULL"))
        if "source" not in cam_columns:
            connection.execute(text("ALTER TABLE cameras ADD COLUMN source VARCHAR(20) DEFAULT 'SIMULATOR' NOT NULL"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_incidents_candidate_id ON incidents (candidate_id)")
        )


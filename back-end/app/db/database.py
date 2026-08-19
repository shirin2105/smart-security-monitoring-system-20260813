import logging
import os

import bcrypt
from sqlalchemy import Boolean, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Camera, User

logger = logging.getLogger("uvicorn.error")


def _is_dev_environment() -> bool:
    """True when running in a local dev or test context.

    In production, user seeding is disabled unless explicit credentials are
    provided via environment variables to avoid shipping known default
    credentials.
    """
    env = os.getenv("ENVIRONMENT", "dev").strip().lower()
    return env in ("dev", "local", "test", "testing")


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

def _seed_default_users(db) -> bool:
    """Seed the default guard and manager users.

    Credentials are sourced from environment variables so that no known
    passwords are ever hard-coded in source:

      - SEED_GUARD_PASSWORD     password for the "guard" user
      - SEED_MANAGER_PASSWORD   password for the "manager" user

    Behaviour:
      - Dev / test environments: fall back to local-only defaults when the
        env var is absent so local development and CI remain functional.
      - Production: seeding is skipped entirely unless both env vars are
        explicitly provided. If only one is provided, that user is seeded
        and the other is skipped (never falls back to a hard-coded value).

    Returns True if any users were seeded.
    """
    guard_pwd = os.getenv("SEED_GUARD_PASSWORD")
    manager_pwd = os.getenv("SEED_MANAGER_PASSWORD")

    if _is_dev_environment():
        guard_pwd = guard_pwd or "guard123"
        manager_pwd = manager_pwd or "manager123"

    if not guard_pwd and not manager_pwd:
        logger.warning(
            "Skipping user seeding: SEED_GUARD_PASSWORD and SEED_MANAGER_PASSWORD "
            "are not set (and ENVIRONMENT is not dev/test)."
        )
        return False

    seeded_any = False

    if guard_pwd:
        guard_user = User(
            username="guard",
            hashed_password=hash_password(guard_pwd),
            role="bao_ve",
            full_name="Bảo Vệ Nguyễn Văn A",
        )
        db.add(guard_user)
        seeded_any = True

    if manager_pwd:
        manager_user = User(
            username="manager",
            hashed_password=hash_password(manager_pwd),
            role="quan_ly",
            full_name="Quản Lý Trần Văn B",
        )
        db.add(manager_user)
        seeded_any = True

    if seeded_any:
        db.commit()
    return seeded_any


def init_db_and_seed():
    Base.metadata.create_all(bind=engine)
    _ensure_incident_ingest_columns()
    db = SessionLocal()
    try:
        # Seed users if empty
        if db.query(User).count() == 0:
            users_seeded = _seed_default_users(db)
            if users_seeded:
                logger.info("Default seed users created: guard, manager")

        # Seed or update cameras
        cameras_seed = [
            (1, "Camera Cổng Chính", "Cổng A - Tầng 1", "/media/walking_people.mp4", False),
            (2, "Camera Sảnh Chờ", "Sảnh Tòa Nhà - Tầng 1", "/media/aboda-video1.mp4", True),
            (3, "Camera Hàng Rào Tây", "Khu Vực Hàng Rào - Phía Tây", "/media/pets2006_3.mp4", True),
            (4, "Camera Phòng Server", "Khai Thác Kỹ Thuật - Tầng Hầm", "/media/aban3.mp4", True),
            (5, "Camera Bãi Xe B1", "Bãi Xe Ô Tự - Tầng B1", "/media/store-aisle-detection.mp4", True),
            (6, "Camera Hành Lang T4", "Hành Lang Văn Phòng - Tầng 4", "/media/person-bicycle-car-detection.mp4", True),
        ]
        for cam_id, name, location, stream_url, ai_enabled in cameras_seed:
            existing = db.query(Camera).filter(Camera.id == cam_id).first()
            if existing:
                existing.stream_url = stream_url
                existing.source = "CV"
                existing.ai_enabled = ai_enabled
            else:
                db.add(Camera(id=cam_id, name=name, location=location, stream_url=stream_url, status="online", source="CV", ai_enabled=ai_enabled))
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
        if "artifact_url" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN artifact_url VARCHAR(2048)"))
        if "redaction_status" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN redaction_status VARCHAR(50) DEFAULT 'COMPLETE'"))
        if "source" not in inc_columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN source VARCHAR(20) DEFAULT 'SIMULATOR' NOT NULL"))
        if "source" not in cam_columns:
            connection.execute(text("ALTER TABLE cameras ADD COLUMN source VARCHAR(20) DEFAULT 'SIMULATOR' NOT NULL"))
        if "ai_enabled" not in cam_columns:
            # Match the ORM model (models.Camera.ai_enabled is Column(Boolean)).
            # Compile the Boolean type for the live dialect so Postgres gets
            # BOOLEAN and SQLite gets BOOLEAN instead of INTEGER, keeping the
            # schema and ORM types consistent across databases.
            ai_enabled_type = Boolean().compile(dialect=engine.dialect)
            connection.execute(
                text(f"ALTER TABLE cameras ADD COLUMN ai_enabled {ai_enabled_type} DEFAULT TRUE NOT NULL")
            )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_incidents_candidate_id ON incidents (candidate_id)")
        )



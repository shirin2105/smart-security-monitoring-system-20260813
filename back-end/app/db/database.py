import os
import logging
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, User, Camera, Incident

logger = logging.getLogger("uvicorn.error")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/security_db"
)

# SQLite fallback URL
SQLITE_FALLBACK_URL = "sqlite:///./security_monitoring.db"

def get_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)

try:
    engine = get_engine(DATABASE_URL)
    with engine.connect() as conn:
        pass
    logger.info(f"Connected successfully to database: {DATABASE_URL}")
except Exception as e:
    logger.warning(f"Could not connect to {DATABASE_URL} ({e}). Falling back to SQLite local database.")
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

        # Seed cameras if empty
        if db.query(Camera).count() == 0:
            cameras_seed = [
                Camera(id=1, name="Camera Cổng Chính", location="Cổng A - Tầng 1", stream_url="https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=600&auto=format&fit=crop", status="online"),
                Camera(id=2, name="Camera Sảnh Chờ", location="Sảnh Tòa Nhà - Tầng 1", stream_url="https://images.unsplash.com/photo-1541888946425-d0fbb186a5b7?w=600&auto=format&fit=crop", status="online"),
                Camera(id=3, name="Camera Hàng Rào Tây", location="Khu Vực Hàng Rào - Phía Tây", stream_url="https://images.unsplash.com/photo-1508873696983-2df515122519?w=600&auto=format&fit=crop", status="warning"),
                Camera(id=4, name="Camera Phòng Server", location="Khai Thác Kỹ Thuật - Tầng Hầm", stream_url="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop", status="online"),
                Camera(id=5, name="Camera Bãi Xe B1", location="Bãi Xe Ô Tô - Tầng B1", stream_url="https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=600&auto=format&fit=crop", status="online"),
                Camera(id=6, name="Camera Hành Lang T4", location="Hành Lang Văn Phòng - Tầng 4", stream_url="https://images.unsplash.com/photo-1517502884422-41eaead166d4?w=600&auto=format&fit=crop", status="online"),
            ]
            db.add_all(cameras_seed)
            db.commit()
            logger.info("6 Default cameras seeded into database")

        # Seed initial sample incident if none
        if db.query(Incident).count() == 0:
            sample_incident = Incident(
                camera_id=3,
                event_type="xam_nhap",
                severity="critical",
                description="Phát hiện đối tượng xâm nhập hàng rào khu vực Phía Tây",
                status="pending"
            )
            db.add(sample_incident)
            db.commit()
            logger.info("Initial sample incident seeded")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

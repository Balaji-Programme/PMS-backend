from sqlalchemy import create_engine, Column, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import logging

from app.core.config import settings

logger = logging.getLogger("app.database")

connect_args = {}
if "azure" in settings.MYSQL_SERVER:
    connect_args = {"ssl": {"ssl_mode": "REQUIRED"}}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Recycle connections before Azure MySQL's 300s idle timeout kills them
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=30,
    pool_recycle=280,   # Azure MySQL idles out at ~300s; stay safely under
    pool_timeout=20,    # Fail fast if no connection available (avoids hanging requests)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class AuditMixin:
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=None, onupdate=func.now(), nullable=True)
    is_active   = Column(Boolean, default=True,  nullable=False)
    is_deleted  = Column(Boolean, default=False, nullable=False)

def get_db():

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

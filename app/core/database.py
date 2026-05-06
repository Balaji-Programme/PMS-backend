from __future__ import annotations

from typing import Generator

from datetime import datetime, timezone
from sqlalchemy import Column, Boolean, DateTime, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from urllib.parse import quote_plus
from logging import getLogger

from app.core.config import settings

logger = getLogger("app.database")

connect_args: dict = {}
if "azure" in settings.MYSQL_SERVER:
    connect_args = {"ssl": {"check_hostname": False}}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

sync_engine = engine

Base = declarative_base()


class AuditMixin:
    created_at = Column(
        DateTime(timezone=False),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.utc_timestamp(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=False),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=True,
    )
    is_active  = Column(Boolean, default=True,  nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)


def ensure_database_exists():
    try:
        encoded_password = quote_plus(settings.MYSQL_PASSWORD)
        server_url = f"mysql+pymysql://{settings.MYSQL_USER}:{encoded_password}@{settings.MYSQL_SERVER}:{settings.MYSQL_PORT}/"
        
        temp_engine = create_engine(server_url, connect_args=connect_args)
        with temp_engine.connect() as conn:

            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DB}"))
        temp_engine.dispose()
        logger.info(f"Ensured database '{settings.MYSQL_DB}' exists.")
    except Exception as e:
        logger.error(f"Failed to ensure database exists: {e}")
        pass

def get_sync_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = get_sync_db

from __future__ import annotations

from typing import Generator

from sqlalchemy import Column, Boolean, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
import ssl
import logging

from app.core.config import settings

logger = logging.getLogger("app.database")

connect_args: dict = {}
if "azure" in settings.MYSQL_SERVER:
    connect_args = {"ssl": {"check_hostname": False}}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=30,
    pool_recycle=280,
    pool_timeout=20,
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
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=None,
        onupdate=func.now(),
        nullable=True,
    )
    is_active  = Column(Boolean, default=True,  nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)


def get_sync_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = get_sync_db

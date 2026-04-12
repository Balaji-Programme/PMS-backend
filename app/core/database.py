from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import logging

from app.core.config import settings

logger = logging.getLogger("app.database")

import ssl

connect_args: dict = {}
if "azure" in settings.MYSQL_SERVER:
    ssl_context = ssl.create_default_context()
    connect_args = {"ssl": ssl_context}

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=30,
    pool_recycle=280,   
    pool_timeout=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

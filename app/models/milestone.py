from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer,
    String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, AuditMixin

class Milestone(AuditMixin, Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    milestone_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    owner_id: Mapped[Optional[int]]   = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    flags: Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)

    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]]   = mapped_column(Date, nullable=True)

    completion_percentage: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    project = relationship("Project", back_populates="milestones", lazy="selectin")
    owner   = relationship("User", foreign_keys=[owner_id], lazy="selectin")

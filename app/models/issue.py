from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey,
    Integer, Numeric, String, Text, Table
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, AuditMixin

class Severity(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

issue_followers = Table(
    "issue_followers",
    Base.metadata,
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

issue_assignees = Table(
    "issue_assignees",
    Base.metadata,
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Issue(AuditMixin, Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    bug_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    associated_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    reporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[Severity]] = mapped_column(SAEnum(Severity), nullable=True)
    
    classification: Mapped[Optional[str]] = mapped_column(String(50), default="None", nullable=True)
    module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    reproducible_flag: Mapped[bool] = mapped_column(Boolean, default=True)

    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    last_closed_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    estimated_hours: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    project  = relationship("Project", back_populates="issues", lazy="selectin")
    reporter = relationship("User", foreign_keys=[reporter_id], lazy="selectin")
    assignee = relationship("User", foreign_keys=[assignee_id], lazy="selectin")

    followers = relationship("User", secondary=issue_followers, lazy="selectin")
    assignees = relationship("User", secondary=issue_assignees, lazy="selectin")

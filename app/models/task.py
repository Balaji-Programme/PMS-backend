from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer,
    Numeric, String, Table, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base, AuditMixin

task_owners = Table(
    "task_owners",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class Task(AuditMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    task_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[Optional[int]]   = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    task_list_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True)
    associated_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    assignee_id: Mapped[Optional[int]]   = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    owner_id: Mapped[Optional[int]]      = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[str]]     = mapped_column(String(500), nullable=True)

    start_date: Mapped[Optional[date]]      = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]]        = mapped_column(Date, nullable=True)
    completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    duration: Mapped[Optional[int]]              = mapped_column(Integer, nullable=True)
    completion_percentage: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)

    estimated_hours: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    work_hours: Mapped[Optional[float]]      = mapped_column(Numeric(5, 2), default=0, nullable=True)
    billing_type: Mapped[str]                = mapped_column(String(50), default="Billable")

    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    project   = relationship("Project", back_populates="tasks", lazy="selectin")
    task_list = relationship("TaskList", back_populates="tasks", lazy="selectin")
    
    assignee     = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    creator      = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    single_owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")

    owners    = relationship("User", secondary=task_owners, lazy="selectin")
    assignees = relationship("User", secondary=task_assignees, lazy="selectin")

    associated_team = relationship("Team", foreign_keys=[associated_team_id], lazy="selectin")

    timelogs: Mapped[List["TimeLog"]] = relationship("TimeLog", back_populates="task", cascade="all, delete-orphan", lazy="selectin")

    @hybrid_property
    def timelog_total(self) -> float:
        if not self.timelogs:
            return 0.0
        return sum(float(log.hours or 0) for log in self.timelogs)

    @hybrid_property
    def difference(self) -> float:
        w_hours = float(self.work_hours or 0)
        return round(w_hours - self.timelog_total, 2)

    @hybrid_property
    def duration(self) -> Optional[int]:
        if self.due_date and self.start_date:
            return (self.due_date - self.start_date).days
        return None

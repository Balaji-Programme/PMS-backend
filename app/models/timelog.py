from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer,
    Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event, select

from app.core.database import Base, AuditMixin

class TimeLog(AuditMixin, Base):
    __tablename__ = "timelogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    task_id: Mapped[Optional[int]]    = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    issue_id: Mapped[Optional[int]]   = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), nullable=True)
    timesheet_id: Mapped[Optional[int]] = mapped_column(ForeignKey("timesheets.id", ondelete="SET NULL"), nullable=True)

    date: Mapped[date] = mapped_column(Date, nullable=False)

    daily_log_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    time_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    billing_type: Mapped[str] = mapped_column(String(50), default="Billable")
    approval_status: Mapped[str] = mapped_column(String(50), default="Pending")
    general_log: Mapped[bool] = mapped_column(Boolean, default=False)

    user       = relationship("User", foreign_keys=[user_id], lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    
    project = relationship("Project", back_populates="timelogs", lazy="selectin")
    task    = relationship("Task", back_populates="timelogs", lazy="selectin")
    issue   = relationship("Issue", lazy="selectin")
    timesheet = relationship("Timesheet", back_populates="timelogs", lazy="selectin")






import sqlalchemy as sa
from sqlalchemy import event, func, update as sa_update


def _recalc_task_total(connection: sa.engine.Connection, task_id: int) -> None:
    
    from app.models.task import Task

    total_row = connection.execute(
        sa.select(func.coalesce(func.sum(TimeLog.daily_log_hours), 0))
        .where(TimeLog.task_id == task_id)
    ).scalar()

    connection.execute(
        sa_update(Task)
        .where(Task.id == task_id)
        .values(cached_timelog_total=float(total_row or 0))
    )


def _on_timelog_insert(mapper, connection, target: TimeLog) -> None:
    if target.task_id:
        _recalc_task_total(connection, target.task_id)


def _on_timelog_update(mapper, connection, target: TimeLog) -> None:
    if target.task_id:
        _recalc_task_total(connection, target.task_id)


def _on_timelog_delete(mapper, connection, target: TimeLog) -> None:
    if target.task_id:
        _recalc_task_total(connection, target.task_id)


event.listen(TimeLog, "after_insert", _on_timelog_insert)
event.listen(TimeLog, "after_update", _on_timelog_update)
event.listen(TimeLog, "after_delete", _on_timelog_delete)


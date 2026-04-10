from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.timelog import TimeLog
from app.models.task import Task
from app.schemas.timelog import TimeLogCreate, TimeLogUpdate
from app.utils.audit_utils import capture_audit_details, write_audit

def _timelog_query():
    return (
        select(TimeLog)
        .options(
            selectinload(TimeLog.user),
            selectinload(TimeLog.project),
            selectinload(TimeLog.task).selectinload(Task.project),
            selectinload(TimeLog.issue),
        )
    )

async def get_timelog(db: AsyncSession, timelog_id: int) -> Optional[TimeLog]:
    result = await db.execute(_timelog_query().where(TimeLog.id == timelog_id))
    return result.scalar_one_or_none()

async def get_timelogs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    issue_id: Optional[int] = None,
    user_emails: Optional[List[str]] = None,
    current_user=None,
) -> List[TimeLog]:
    stmt = _timelog_query()

    if project_id:
        stmt = stmt.outerjoin(Task, TimeLog.task_id == Task.id).where(
            or_(TimeLog.project_id == project_id, Task.project_id == project_id)
        )
    if task_id:
        stmt = stmt.where(TimeLog.task_id == task_id)
    if issue_id:
        stmt = stmt.where(TimeLog.issue_id == issue_id)
    if user_emails:
        stmt = stmt.where(TimeLog.user_email.in_(user_emails))
    if current_user is not None:
        stmt = stmt.where(TimeLog.user_email == current_user.email)

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().unique().all()

async def create_timelog(
    db: AsyncSession,
    timelog: TimeLogCreate,
    actor_id: Optional[str] = None,
) -> TimeLog:
    db_timelog = TimeLog(
        user_email      = timelog.user_email,
        project_id      = timelog.project_id,
        task_id         = timelog.task_id,
        issue_id        = timelog.issue_id,
        date            = timelog.date,
        hours           = timelog.hours,
        description     = timelog.description,
        log_title       = timelog.log_title,
        billing_type    = timelog.billing_type,
        approval_status = timelog.approval_status,
        general_log     = timelog.general_log,
    )
    db.add(db_timelog)
    await db.flush()

    await write_audit(
        db, actor_id, "CREATE", "timelogs",
        timelog.project_id or db_timelog.id, db_timelog.id,
        [{"field_name": "hours", "old_value": None,
          "new_value": f"{timelog.hours}h on {timelog.date} — {timelog.log_title or timelog.description or ''}"}],
    )
    await db.commit()
    return await get_timelog(db, db_timelog.id)

async def update_timelog(
    db: AsyncSession,
    timelog_id: int,
    timelog_update: TimeLogUpdate,
    actor_id: Optional[str] = None,
) -> Optional[TimeLog]:
    result = await db.execute(select(TimeLog).where(TimeLog.id == timelog_id))
    db_timelog = result.scalar_one_or_none()
    if not db_timelog:
        return None

    update_data = timelog_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_timelog, update_data)
    for key, value in update_data.items():
        setattr(db_timelog, key, value)

    await write_audit(db, actor_id, "UPDATE", "timelogs",
                      db_timelog.project_id or timelog_id, timelog_id, changes)
    await db.commit()
    return await get_timelog(db, timelog_id)

async def delete_timelog(
    db: AsyncSession,
    timelog_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = await db.execute(select(TimeLog).where(TimeLog.id == timelog_id))
    db_timelog = result.scalar_one_or_none()
    if not db_timelog:
        return False
    await write_audit(
        db, actor_id, "DELETE", "timelogs",
        db_timelog.project_id or timelog_id, timelog_id,
        [{"field_name": "hours", "old_value": str(db_timelog.hours), "new_value": None}],
    )
    await db.delete(db_timelog)
    await db.commit()
    return True

async def create_timelogs_bulk(
    db: AsyncSession,
    timelogs: List[TimeLogCreate],
    actor_id: Optional[str] = None,
) -> List[TimeLog]:
    db_logs = []
    for log in timelogs:
        if log.hours <= 0:
            continue
        db_log = TimeLog(
            user_email      = log.user_email,
            project_id      = log.project_id,
            task_id         = log.task_id,
            issue_id        = log.issue_id,
            date            = log.date,
            hours           = log.hours,
            description     = log.description,
            log_title       = log.log_title,
            billing_type    = log.billing_type,
            approval_status = log.approval_status,
            general_log     = log.general_log,
        )
        db_logs.append(db_log)
        db.add(db_log)

    await db.flush()
    await db.commit()
    for db_log in db_logs:
        await db.refresh(db_log)

    if actor_id and db_logs:
        await write_audit(
            db, actor_id, "CREATE", "timelogs",
            db_logs[0].project_id or db_logs[0].id, db_logs[0].id,
            [{"field_name": "bulk_create", "old_value": None,
              "new_value": f"Bulk created {len(db_logs)} time logs"}],
        )

    return db_logs

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import capture_audit_details, write_audit

def _task_query():
    return (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.task_list),
            selectinload(Task.associated_team),  
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.single_owner),
            selectinload(Task.owners),
            selectinload(Task.assignees),
            selectinload(Task.timelogs),  
        )
    )

async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    result = await db.execute(_task_query().where(Task.id == task_id))
    return result.scalar_one_or_none()

async def get_tasks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = None,
) -> dict:
    stmt = _task_query()

    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    items_result = await db.execute(stmt.offset(skip).limit(limit))
    return {"total": total, "items": items_result.scalars().unique().all()}

async def create_task(
    db: AsyncSession,
    task: TaskCreate,
    actor_id: Optional[str] = None,
) -> Task:
    
    db_task = Task(
        public_id             = generate_public_id("TSK-"),
        task_name             = task.task_name,
        description           = task.description,
        project_id            = task.project_id,
        task_list_id          = task.task_list_id,
        associated_team_id    = task.associated_team_id,
        assignee_id           = task.assignee_id,
        owner_id              = task.owner_id,
        status                = task.status,
        priority              = task.priority,
        tags                  = task.tags,
        start_date            = task.start_date,
        due_date              = task.due_date,
        duration              = task.duration,
        completion_percentage = task.completion_percentage,
        estimated_hours       = task.estimated_hours,
        work_hours            = task.work_hours,
        billing_type          = task.billing_type,
    )

    if task.owner_emails:
        owners = (await db.execute(select(User).where(User.email.in_(task.owner_emails)))).scalars().all()
        db_task.owners.extend(owners)
    if task.assignee_emails:
        assignees = (await db.execute(select(User).where(User.email.in_(task.assignee_emails)))).scalars().all()
        db_task.assignees.extend(assignees)

    db.add(db_task)
    await db.flush()

    await write_audit(
        db, actor_id, "CREATE", "tasks",
        task.project_id or db_task.id, db_task.id,
        [{"field_name": "task_name", "old_value": None, "new_value": task.task_name}],
    )
    await db.commit()
    return await get_task(db, db_task.id)

async def update_task(
    db: AsyncSession,
    task_id: int,
    task_update: TaskUpdate,
    actor_id: Optional[str] = None,
) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return None

    update_data = task_update.model_dump(exclude_unset=True, exclude={"owner_emails", "assignee_emails"})
    changes = capture_audit_details(db_task, update_data)

    for key, value in update_data.items():
        setattr(db_task, key, value)

    if task_update.owner_emails is not None:
        owners = (await db.execute(select(User).where(User.email.in_(task_update.owner_emails)))).scalars().all()
        db_task.owners = list(owners)

    if task_update.assignee_emails is not None:
        assignees = (await db.execute(select(User).where(User.email.in_(task_update.assignee_emails)))).scalars().all()
        db_task.assignees = list(assignees)

    await write_audit(db, actor_id, "UPDATE", "tasks", db_task.project_id or task_id, task_id, changes)
    await db.commit()
    return await get_task(db, task_id)

async def delete_task(
    db: AsyncSession,
    task_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return False
        
    await write_audit(db, actor_id, "DELETE", "tasks", db_task.project_id or task_id, task_id, [])
    await db.delete(db_task)
    await db.commit()
    return True

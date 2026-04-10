from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_list import TaskList
from app.schemas.task_list import TaskListCreate, TaskListUpdate
from app.utils.audit_utils import capture_audit_details, write_audit

def _tl_query():
    return select(TaskList).options(selectinload(TaskList.project))

async def get_task_list(db: AsyncSession, task_list_id: int) -> Optional[TaskList]:
    result = await db.execute(_tl_query().where(TaskList.id == task_list_id))
    return result.scalar_one_or_none()

async def get_task_lists(
    db: AsyncSession,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[TaskList]:
    stmt = _tl_query()
    if project_id:
        stmt = stmt.where(TaskList.project_id == project_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().unique().all()

async def create_task_list(
    db: AsyncSession,
    task_list: TaskListCreate,
    actor_id: Optional[str] = None,
) -> TaskList:
    db_tl = TaskList(
        name        = task_list.name,
        description = task_list.description,
        project_id  = task_list.project_id,
    )
    db.add(db_tl)
    await db.flush()

    await write_audit(
        db, actor_id, "CREATE", "task_lists",
        task_list.project_id or db_tl.id, db_tl.id,
        [{"field_name": "name", "old_value": None, "new_value": task_list.name}],
    )
    await db.commit()
    return await get_task_list(db, db_tl.id)

async def update_task_list(
    db: AsyncSession,
    task_list_id: int,
    task_list_update: TaskListUpdate,
    actor_id: Optional[str] = None,
) -> Optional[TaskList]:
    result = await db.execute(select(TaskList).where(TaskList.id == task_list_id))
    db_tl = result.scalar_one_or_none()
    if not db_tl:
        return None

    update_data = task_list_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_tl, update_data)
    for k, v in update_data.items():
        setattr(db_tl, k, v)

    await write_audit(db, actor_id, "UPDATE", "task_lists", db_tl.project_id or task_list_id, task_list_id, changes)
    await db.commit()
    return await get_task_list(db, task_list_id)

async def delete_task_list(
    db: AsyncSession,
    task_list_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = await db.execute(select(TaskList).where(TaskList.id == task_list_id))
    db_tl = result.scalar_one_or_none()
    if not db_tl:
        return False
    await write_audit(
        db, actor_id, "DELETE", "task_lists",
        db_tl.project_id or task_list_id, task_list_id,
        [{"field_name": "name", "old_value": db_tl.name, "new_value": None}],
    )
    await db.delete(db_tl)
    await db.commit()
    return True

async def search_task_lists(
    db: AsyncSession,
    query: str,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> List[TaskList]:
    if not query:
        return []
    stmt = _tl_query().where(TaskList.name.ilike(f"%{query}%"))
    if project_id:
        stmt = stmt.where(TaskList.project_id == project_id)
    result = await db.execute(stmt.limit(limit))
    return result.scalars().unique().all()

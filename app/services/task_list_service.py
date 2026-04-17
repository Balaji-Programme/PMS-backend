from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.task_list import TaskList
from app.schemas.task_list import TaskListCreate, TaskListUpdate
from app.utils.audit_utils import capture_audit_details, write_audit

def _tl_query():
    return select(TaskList).options(selectinload(TaskList.project))

def get_task_list(db: Session, task_list_id: int) -> Optional[TaskList]:
    result = db.execute(_tl_query().where(TaskList.id == task_list_id))
    return result.scalar_one_or_none()

def get_task_lists(
    db: Session,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[TaskList]:
    stmt = _tl_query()
    if project_id:
        stmt = stmt.where(TaskList.project_id == project_id)
    result = db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().unique().all()

def create_task_list(
    db: Session,
    task_list: TaskListCreate,
    actor_id: Optional[str] = None,
) -> TaskList:
    db_tl = TaskList(
        name        = task_list.name,
        description = task_list.description,
        project_id  = task_list.project_id,
    )
    db.add(db_tl)
    db.flush()

    write_audit(
        db, actor_id, "CREATE", "task_lists",
        task_list.project_id or db_tl.id, db_tl.id,
        [{"field_name": "name", "old_value": None, "new_value": task_list.name}],
    )
    db.commit()
    return get_task_list(db, db_tl.id)

def update_task_list(
    db: Session,
    task_list_id: int,
    task_list_update: TaskListUpdate,
    actor_id: Optional[str] = None,
) -> Optional[TaskList]:
    result = db.execute(select(TaskList).where(TaskList.id == task_list_id))
    db_tl = result.scalar_one_or_none()
    if not db_tl:
        return None

    update_data = task_list_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_tl, update_data)
    for k, v in update_data.items():
        setattr(db_tl, k, v)

    write_audit(db, actor_id, "UPDATE", "task_lists", db_tl.project_id or task_list_id, task_list_id, changes)
    db.commit()
    return get_task_list(db, task_list_id)

def delete_task_list(
    db: Session,
    task_list_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = db.execute(select(TaskList).where(TaskList.id == task_list_id))
    db_tl = result.scalar_one_or_none()
    if not db_tl:
        return False
    write_audit(
        db, actor_id, "DELETE", "task_lists",
        db_tl.project_id or task_list_id, task_list_id,
        [{"field_name": "name", "old_value": db_tl.name, "new_value": None}],
    )
    db.delete(db_tl)
    db.commit()
    return True

def search_task_lists(
    db: Session,
    query: str,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> List[TaskList]:
    if not query:
        return []
    stmt = _tl_query().where(TaskList.name.ilike(f"%{query}%"))
    if project_id:
        stmt = stmt.where(TaskList.project_id == project_id)
    result = db.execute(stmt.limit(limit))
    return result.scalars().unique().all()

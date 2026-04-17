from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.ids import generate_public_id, get_next_sequence_id
from app.models.project import Project
from app.utils.audit_utils import capture_audit_details, write_audit


def _task_query():
    return (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.task_list),
            selectinload(Task.milestone),
            selectinload(Task.associated_team),
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.single_owner),
            selectinload(Task.owners),
            selectinload(Task.assignees),
            selectinload(Task.timelogs),
            selectinload(Task.status_master),
            selectinload(Task.priority_master),
        )
    )


def get_task(db: Session, task_id: int) -> Optional[Task]:
    result = db.execute(_task_query().where(Task.id == task_id))
    return result.scalar_one_or_none()


def get_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status_ids: Optional[List[int]] = None,
    priority_ids: Optional[List[int]] = None,
    assignee_emails: Optional[List[str]] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> dict:
    stmt = _task_query()

    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status_ids:
        stmt = stmt.where(Task.status_id.in_(status_ids))
    if priority_ids:
        stmt = stmt.where(Task.priority_id.in_(priority_ids))


    if assignee_emails:
        stmt = (
            stmt.join(User, User.id == Task.assignee_id)
            .where(User.email.in_(assignee_emails))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (db.execute(count_stmt)).scalar() or 0
    items_result = db.execute(stmt.offset(skip).limit(limit))
    return {"total": total, "items": items_result.scalars().unique().all()}


def search_tasks(
    db: Session,
    query: str,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> List[Task]:
    if not query:
        return []
    q = f"%{query}%"
    stmt = _task_query().where(
        or_(Task.task_name.ilike(q), Task.public_id.ilike(q))
    )
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    result = db.execute(stmt.limit(limit))
    return result.scalars().unique().all()


def create_task(
    db: Session,
    task: TaskCreate,
    actor_id: Optional[str] = None,
    created_by_id: Optional[int] = None,
) -> Task:
    project = None
    if task.project_id:
        project = db.execute(select(Project).where(Project.id == task.project_id)).scalar_one_or_none()
    
    project_name = project.project_name if project else ""
    public_id = get_next_sequence_id(db, Task, project_name, task.project_id, "T") if task.project_id else generate_public_id("TSK-")

    db_task = Task(
        public_id             = public_id,
        task_name             = task.task_name,
        description           = task.description,
        project_id            = task.project_id,
        task_list_id          = task.task_list_id,
        milestone_id          = task.milestone_id,
        associated_team_id    = task.associated_team_id,
        assignee_id           = task.assignee_id,
        owner_id              = task.owner_id,
        created_by_id         = created_by_id,
        status_id             = task.status_id,
        priority_id           = task.priority_id,
        tags                  = task.tags,
        start_date            = task.start_date,
        due_date              = task.due_date,
        duration              = task.duration,
        completion_percentage = task.completion_percentage or 0,
        estimated_hours       = task.estimated_hours,
        work_hours            = task.work_hours or 0.0,
        billing_type          = task.billing_type or "Billable",
    )

    if task.owner_emails:
        owners = (
            db.execute(select(User).where(User.email.in_(task.owner_emails)))
        ).scalars().all()
        db_task.owners.extend(owners)

    if task.assignee_emails:
        assignees = (
            db.execute(select(User).where(User.email.in_(task.assignee_emails)))
        ).scalars().all()
        db_task.assignees.extend(assignees)

    db.add(db_task)
    db.flush()

    write_audit(
        db, actor_id, "CREATE", "tasks",
        task.project_id or db_task.id, db_task.id,
        [{"field_name": "task_name", "old_value": None, "new_value": task.task_name}],
    )
    db.commit()
    return get_task(db, db_task.id)


def update_task(
    db: Session,
    task_id: int,
    task_update: TaskUpdate,
    actor_id: Optional[str] = None,
) -> Optional[Task]:
    result = db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return None

    update_data = task_update.model_dump(
        exclude_unset=True,
        exclude={"owner_emails", "assignee_emails"},
    )
    changes = capture_audit_details(db_task, update_data)
    for key, value in update_data.items():
        setattr(db_task, key, value)

    if task_update.owner_emails is not None:
        owners = (
            db.execute(select(User).where(User.email.in_(task_update.owner_emails)))
        ).scalars().all()
        db_task.owners = list(owners)

    if task_update.assignee_emails is not None:
        assignees = (
            db.execute(select(User).where(User.email.in_(task_update.assignee_emails)))
        ).scalars().all()
        db_task.assignees = list(assignees)

    write_audit(
        db, actor_id, "UPDATE", "tasks",
        db_task.project_id or task_id, task_id, changes,
    )
    db.commit()
    return get_task(db, task_id)


def delete_task(
    db: Session,
    task_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return False
    write_audit(
        db, actor_id, "DELETE", "tasks",
        db_task.project_id or task_id, task_id, [],
    )
    db.delete(db_task)
    db.commit()
    return True

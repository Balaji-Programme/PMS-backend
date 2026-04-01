from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details

def get_task(db: Session, task_id: int):
    return db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignee),
        joinedload(Task.assignees),
        joinedload(Task.owners),
        joinedload(Task.status),
        joinedload(Task.priority)
    ).filter(Task.id == task_id).first()

def get_tasks(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    project_id: int = None,
    status_ids: Optional[List[int]] = None,
    priority_ids: Optional[List[int]] = None,
    assignee_emails: Optional[List[str]] = None
):
    query = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.task_list),
        joinedload(Task.creator),
        joinedload(Task.assignee),
        joinedload(Task.assignees),
        joinedload(Task.owners),
        joinedload(Task.status),
        joinedload(Task.priority)
    )
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    if status_ids:
        query = query.filter(Task.status_id.in_(status_ids))
    if priority_ids:
        query = query.filter(Task.priority_id.in_(priority_ids))
    if assignee_emails:
        query = query.filter(Task.assignee_email.in_(assignee_emails))
        
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"total": total, "items": items}

def create_task(db: Session, task: TaskCreate, actor_id: Optional[str] = None):
    public_id = generate_public_id("TSK-")
    db_task = Task(
        public_id=public_id,
        title=task.title,
        description=task.description,
        project_id=task.project_id,
        task_list_id=task.task_list_id,
        assignee_email=task.assignee_email,
        status_id=task.status_id,
        priority_id=task.priority_id,
        start_date=task.start_date,
        end_date=task.end_date,
        due_date=task.end_date or task.due_date,
        progress=task.progress,
        estimated_hours=task.estimated_hours,
        billing_type=task.billing_type,
        created_by_email=task.created_by_email
    )
    if task.owner_ids:
        owners = db.query(User).filter(User.id.in_(task.owner_ids)).all()
        db_task.owners.extend(owners)
    
    if task.assignee_ids:
        assignees = db.query(User).filter(User.id.in_(task.assignee_ids)).all()
        db_task.assignees.extend(assignees)

    db.add(db_task)
    db.flush()

    write_audit(db, actor_id, "CREATE", "tasks",
                resource_id=task.project_id or db_task.id,
                record_id=db_task.id,
                details=[{"field_name": "title", "old_value": None, "new_value": task.title}])

    db.commit()
    db.refresh(db_task)
    return get_task(db, db_task.id)

def update_task(db: Session, task_id: int, task_update: TaskUpdate, actor_id: Optional[str] = None):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        return None
    
    # Exclude M2M ID lists from the setattr loop — those are handled separately below
    update_data = task_update.model_dump(exclude_unset=True, exclude={'owner_ids', 'assignee_ids'})
    changes = capture_audit_details(db_task, update_data)

    for key, value in update_data.items():
        setattr(db_task, key, value)

    if hasattr(task_update, 'owner_ids') and task_update.owner_ids is not None:
        owners = db.query(User).filter(User.id.in_(task_update.owner_ids)).all()
        db_task.owners = owners

    if hasattr(task_update, 'assignee_ids') and task_update.assignee_ids is not None:
        assignees = db.query(User).filter(User.id.in_(task_update.assignee_ids)).all()
        db_task.assignees = assignees

    write_audit(db, actor_id, "UPDATE", "tasks",
                resource_id=db_task.project_id or task_id,
                record_id=task_id,
                details=changes)

    db.commit()
    db.refresh(db_task)
    return get_task(db, db_task.id)

def delete_task(db: Session, task_id: int, actor_id: Optional[str] = None):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if db_task:
        write_audit(db, actor_id, "DELETE", "tasks",
                    resource_id=db_task.project_id or task_id,
                    record_id=task_id,
                    details=[{"field_name": "title", "old_value": db_task.title, "new_value": None}])
        db.delete(db_task)
        db.commit()
        return True
    return False

def search_tasks(db: Session, query: str, project_id: int = None, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    from sqlalchemy import or_
    query_obj = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignee),
        joinedload(Task.status)
    )
    if project_id:
        query_obj = query_obj.filter(Task.project_id == project_id)
    
    return query_obj.filter(
        or_(
            Task.title.ilike(q),
            Task.public_id.ilike(q)
        )
    ).limit(limit).all()

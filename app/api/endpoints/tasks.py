from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import (
    allow_authenticated, allow_team_lead_plus, allow_pm,
    is_employee_only, is_team_lead_plus
)
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.services import task_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TaskResponse, dependencies=[Depends(allow_team_lead_plus)])
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(allow_team_lead_plus)
):
    """Only Team Lead and above can create tasks."""
    if not task.created_by_email:
        task.created_by_email = current_user.email
    return task_service.create_task(db=db, task=task, actor_id=current_user.o365_id or str(current_user.id))

@router.post("/bulk", response_model=List[TaskResponse], dependencies=[Depends(allow_team_lead_plus)])
def bulk_create_tasks(tasks: List[TaskCreate], db: Session = Depends(get_db), current_user = Depends(allow_team_lead_plus)):
    """Only Team Lead and above can bulk create tasks."""
    return [task_service.create_task(db=db, task=t, actor_id=current_user.o365_id or str(current_user.id)) for t in tasks]

@router.get("/search", response_model=List[TaskResponse])
def search_tasks(
    q: str = Query(..., min_length=1),
    project_id: int = Query(None),
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(allow_authenticated)
):
    return task_service.search_tasks(db, query=q, project_id=project_id, limit=limit)

@router.get("/", response_model=TaskListResponse)
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    project_id: Optional[int] = None, 
    status_id: Optional[List[int]] = Query(None),
    priority_id: Optional[List[int]] = Query(None),
    assignee_email: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(allow_authenticated)
):
    """
    Retrieve tasks with total count. Employees only see tasks assigned to them.
    """
    if is_employee_only(current_user):
        assignee_email = [current_user.email]

    return task_service.get_tasks(
        db, 
        skip=skip, 
        limit=limit, 
        project_id=project_id,
        status_ids=status_id,
        priority_ids=priority_id,
        assignee_emails=assignee_email
    )

@router.get("/{task_id}", response_model=TaskResponse)
def read_task(task_id: int, db: Session = Depends(get_db), current_user = Depends(allow_authenticated)):
    db_task = task_service.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    # Employee can only view tasks assigned to them
    if is_employee_only(current_user) and db_task.assignee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied: you are not assigned to this task.")
    return db_task

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user = Depends(allow_authenticated)):
    db_task = task_service.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    # Employee can only update tasks assigned to them
    if is_employee_only(current_user) and db_task.assignee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied: you can only update tasks assigned to you.")
    
    updated = task_service.update_task(db, task_id=task_id, task_update=task, actor_id=current_user.o365_id or str(current_user.id))
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated

@router.delete("/{task_id}", dependencies=[Depends(allow_team_lead_plus)])
def delete_task(task_id: int, db: Session = Depends(get_db), current_user = Depends(allow_team_lead_plus)):
    """Only Team Lead and above can delete tasks."""
    success = task_service.delete_task(db, task_id=task_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

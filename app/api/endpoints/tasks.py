from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import allow_authenticated, allow_team_lead_plus, check_task_owner_or_lead, is_employee_only
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.services import task_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_team_lead_plus),
):
    if not task.created_by_email:
        task.created_by_email = current_user.email
    return await task_service.create_task(db=db, task=task, actor_id=current_user.o365_id or str(current_user.id))

@router.post("/bulk", response_model=List[TaskResponse])
async def bulk_create_tasks(
    tasks: List[TaskCreate],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_team_lead_plus),
):
    results = []
    for t in tasks:
        if not t.created_by_email:
            t.created_by_email = current_user.email
        results.append(await task_service.create_task(db=db, task=t, actor_id=current_user.o365_id or str(current_user.id)))
    return results

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=1),
    project_id: Optional[int] = Query(None),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await task_service.search_tasks(db, query=q, project_id=project_id, limit=limit)

@router.get("/", response_model=TaskListResponse)
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status_id: Optional[List[int]] = Query(None),
    priority_id: Optional[List[int]] = Query(None),
    assignee_email: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    if is_employee_only(current_user):
        assignee_email = [current_user.email]
    return await task_service.get_tasks(
        db,
        skip            = skip,
        limit           = limit,
        project_id      = project_id,
        status_ids      = status_id,
        priority_ids    = priority_id,
        assignee_emails = assignee_email,
    )

@router.get("/{task_id}", response_model=TaskResponse)
async def read_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    db_task = await task_service.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if is_employee_only(current_user) and db_task.assignee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied: you are not assigned to this task.")
    return db_task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_task_owner_or_lead),
):
    updated = await task_service.update_task(db, task_id=task_id, task_update=task, actor_id=current_user.public_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_task_owner_or_lead),
):
    success = await task_service.delete_task(db, task_id=task_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

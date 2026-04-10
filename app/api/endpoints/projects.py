from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    allow_authenticated,
    allow_pm,
    allow_team_lead_plus,
    check_project_owner_or_pm,
    check_project_owner_or_lead,
    is_employee_only,
)
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectUserCreate, ProjectSyncUpdate
from app.schemas.audit import AuditLogResponse
from app.services import project_service
from app.services.teams_automation import create_ms_team_for_project

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    project: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_pm),
):
    db_project = await project_service.create_project(
        db=db, project=project, actor_id=current_user.public_id
    )

    from app.services.ms_teams_service import MSTeamsService
    member_emails = project.user_emails or []
    background_tasks.add_task(
        MSTeamsService.create_ms_team,
        project_name  = db_project.project_name,
        members       = member_emails,
    )

    return db_project

@router.get("/search", response_model=List[ProjectResponse])
async def search_projects(
    q: str = Query(..., min_length=1),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await project_service.search_projects(db, query=q, limit=limit)

@router.get("/", response_model=List[ProjectResponse])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    status_id: Optional[List[int]] = Query(None),
    priority_id: Optional[List[int]] = Query(None),
    manager_email: Optional[List[str]] = Query(None),
    is_archived: Optional[bool] = Query(None),
    is_template: Optional[bool] = Query(None),
    include_all: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    return await project_service.get_projects(
        db,
        skip          = skip,
        limit         = limit,
        status_ids    = status_id,
        priority_ids  = priority_id,
        manager_emails = manager_email,
        is_archived   = is_archived,
        is_template   = is_template,
        include_all   = include_all,
        current_user  = current_user if is_employee_only(current_user) else None,
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    db_project = await project_service.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if is_employee_only(current_user):
        if current_user.email not in {u.email for u in db_project.users}:
            raise HTTPException(status_code=403, detail="You are not a member of this project.")
    return db_project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_project_owner_or_lead),
):
    db_project = await project_service.update_project(
        db, project_id=project_id, project_update=project, actor_id=current_user.o365_id
    )
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_project_owner_or_pm),
):
    success = await project_service.delete_project(
        db, project_id=project_id, actor_id=current_user.o365_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

@router.patch("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_project_owner_or_pm),
):
    result = await project_service.archive_project(db, project_id, archived=True)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result

@router.patch("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(check_project_owner_or_pm),
):
    result = await project_service.archive_project(db, project_id, archived=False)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result

@router.post("/{project_id}/sync", response_model=ProjectResponse)
async def sync_project(
    project_id: int,
    sync_data: ProjectSyncUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_pm),
):
    result = await project_service.sync_project_fields(
        db, project_id=project_id, sync_data=sync_data, actor_id=current_user.o365_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result

@router.get("/{project_id}/audit", response_model=List[AuditLogResponse])
async def get_project_audit_logs(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.audit import AuditLogs

    result = await db.execute(
        select(AuditLogs)
        .where(
            AuditLogs.TableName == "projects",
            AuditLogs.Comments.like(f"%Record ID: {project_id}%"),
        )
        .order_by(AuditLogs.PerformedOn.desc())
    )
    return result.scalars().all()

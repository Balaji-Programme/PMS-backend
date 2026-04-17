from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_sync_db
from app.core.security import allow_authenticated, allow_pm
from app.schemas.template import (
    ProjectTemplateCreate,
    ProjectTemplateUpdate,
    ProjectTemplateResponse,
    TemplateTaskCreate,
    TemplateTaskResponse,
)
from app.services import template_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])


@router.get("/", response_model=List[ProjectTemplateResponse])
def list_templates(db: Session = Depends(get_sync_db)):
    
    return template_service.get_templates(db)


@router.get("/{template_id}", response_model=ProjectTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_sync_db)):
    tmpl = template_service.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("/", response_model=ProjectTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    data: ProjectTemplateCreate,
    db: Session = Depends(get_sync_db),
    current_user=Depends(allow_authenticated),
):
    
    return template_service.create_template(db, data, created_by_id=current_user.id)


@router.put("/{template_id}", response_model=ProjectTemplateResponse)
def update_template(
    template_id: int,
    data: ProjectTemplateUpdate,
    db: Session = Depends(get_sync_db),
    _=Depends(allow_authenticated),
):
    
    tmpl = template_service.update_template(db, template_id, data)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl




@router.post(
    "/{template_id}/tasks",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_task(
    template_id: int,
    task: TemplateTaskCreate,
    db: Session = Depends(get_sync_db),
    _=Depends(allow_authenticated),
):
    
    tmpl = template_service.add_template_task(db, template_id, task.model_dump())
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.delete(
    "/{template_id}/tasks/{task_id}",
    response_model=ProjectTemplateResponse,
)
def remove_task(
    template_id: int,
    task_id: int,
    db: Session = Depends(get_sync_db),
    _=Depends(allow_authenticated),
):
    
    tmpl = template_service.remove_template_task(db, template_id, task_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template or task not found")
    return tmpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_sync_db),
    _=Depends(allow_authenticated),
):
    success = template_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

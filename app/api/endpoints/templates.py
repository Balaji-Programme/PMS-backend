from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import allow_authenticated, allow_pm
from app.schemas.template import ProjectTemplateCreate, ProjectTemplateResponse
from app.services import template_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/", response_model=List[ProjectTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    return await template_service.get_templates(db)

@router.get("/{template_id}", response_model=ProjectTemplateResponse)
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    tmpl = await template_service.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl

@router.post("/", response_model=ProjectTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: ProjectTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_pm),
):
    return await template_service.create_template(db, data, created_by_id=current_user.id)

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(allow_pm),
):
    success = await template_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_sync_db
from app.core.security import allow_authenticated
from app.schemas.project_group import ProjectGroupCreate, ProjectGroupResponse, ProjectGroupUpdate
from app.services import project_group_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/", response_model=List[ProjectGroupResponse])
def read_project_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_sync_db)):
    return project_group_service.get_project_groups(db, skip=skip, limit=limit)

@router.get("/search", response_model=List[ProjectGroupResponse])
def search_project_groups(
    q: str = Query(..., min_length=1),
    limit: int = 20,
    db: Session = Depends(get_sync_db)
):
    return project_group_service.search_project_groups(db, query=q, limit=limit)

@router.post("/", response_model=ProjectGroupResponse)
def create_project_group(group: ProjectGroupCreate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    return project_group_service.create_project_group(db, group, actor_id=current_user.o365_id or str(current_user.id))

@router.get("/{group_id}", response_model=ProjectGroupResponse)
def read_project_group(group_id: int, db: Session = Depends(get_sync_db)):
    db_group = project_group_service.get_project_group(db, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Project group not found")
    return db_group

@router.put("/{group_id}", response_model=ProjectGroupResponse)
def update_project_group(group_id: int, group: ProjectGroupUpdate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    db_group = project_group_service.update_project_group(db, group_id, group, actor_id=current_user.o365_id or str(current_user.id))
    if not db_group:
        raise HTTPException(status_code=404, detail="Project group not found")
    return db_group

@router.delete("/{group_id}")
def delete_project_group(group_id: int, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    success = project_group_service.delete_project_group(db, group_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Project group not found")
    return {"message": "Project group deleted successfully"}

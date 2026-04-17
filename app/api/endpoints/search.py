from typing import Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_sync_db
from app.core.security import allow_authenticated
from app.services.search_service import search_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/", response_model=List[Any])
def global_search(
    db: Session = Depends(get_sync_db),
    q: str = Query(..., min_length=1),
    limit: int = Query(15, gt=0, le=100)
) -> Any:

    return search_service.global_search(db, query=q, limit=limit)

@router.get("/work-items", response_model=List[Any])
def search_work_items(
    db: Session = Depends(get_sync_db),
    q: str = Query("", min_length=0),
    project_id: int = Query(None),
    limit: int = Query(15, gt=0, le=100)
) -> Any:

    return search_service.search_work_items(db, query=q, project_id=project_id, limit=limit)

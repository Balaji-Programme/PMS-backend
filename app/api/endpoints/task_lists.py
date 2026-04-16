from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_sync_db
from app.core.security import allow_authenticated
from app.schemas.task_list import TaskListCreate, TaskListResponse, TaskListUpdate
from app.services import task_list_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TaskListResponse)
def create_task_list(
    task_list: TaskListCreate,
    db: Session = Depends(get_sync_db),
    current_user = Depends(allow_authenticated)
):
    try:
        return task_list_service.create_task_list(db=db, task_list=task_list, actor_id=current_user.o365_id or str(current_user.id))
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        with open("error_log.txt", "a") as f:
            f.write("\nTASKLIST ERROR:\n" + err)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=List[TaskListResponse])
def search_task_lists(
    q: str = Query(..., min_length=1),
    project_id: int = Query(None),
    limit: int = 20,
    db: Session = Depends(get_sync_db)
):
    return task_list_service.search_task_lists(db, query=q, project_id=project_id, limit=limit)

@router.get("/", response_model=List[TaskListResponse])
def read_task_lists(
    project_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_sync_db)
):
    return task_list_service.get_task_lists(db, skip=skip, limit=limit, project_id=project_id)

@router.get("/{task_list_id}", response_model=TaskListResponse)
def read_task_list(
    task_list_id: int,
    db: Session = Depends(get_sync_db)
):
    db_task_list = task_list_service.get_task_list(db, task_list_id=task_list_id)
    if db_task_list is None:
        raise HTTPException(status_code=404, detail="Task List not found")
    return db_task_list

@router.put("/{task_list_id}", response_model=TaskListResponse)
def update_task_list(
    task_list_id: int,
    task_list_in: TaskListUpdate,
    db: Session = Depends(get_sync_db),
    current_user = Depends(allow_authenticated)
):
    custom = task_list_service.update_task_list(db, task_list_id, task_list_in, actor_id=current_user.o365_id or str(current_user.id))
    if not custom:
        raise HTTPException(status_code=404, detail="Task List not found")
    return custom

@router.delete("/{task_list_id}")
def delete_task_list(
    task_list_id: int,
    db: Session = Depends(get_sync_db),
    current_user = Depends(allow_authenticated)
):
    success = task_list_service.delete_task_list(db, task_list_id=task_list_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Task List not found")
    return {"message": "Task List deleted successfully"}

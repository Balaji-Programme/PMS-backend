from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import allow_authenticated, allow_team_lead_plus, is_employee_only
from app.core.dependencies import auto_populate_timelog
from app.schemas.timelog import TimeLogCreate, TimeLogUpdate, TimeLogResponse, TimeLogBulkCreate
from app.services import timelog_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TimeLogResponse)
def create_timelog(
    timelog: TimeLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):

    auto_populate_timelog(timelog, current_user)
    if is_employee_only(current_user):
        timelog.user_email = current_user.email

    return timelog_service.create_timelog(
        db=db,
        timelog=timelog,
        actor_id=current_user.o365_id or str(current_user.id),
    )

@router.post("/bulk", response_model=List[TimeLogResponse])
def create_timelogs_bulk(
    bulk: TimeLogBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):

    for log in bulk.logs:
        auto_populate_timelog(log, current_user)
        if is_employee_only(current_user):
            log.user_email = current_user.email
            
    return timelog_service.create_timelogs_bulk(
        db=db,
        timelogs=bulk.logs,
        actor_id=current_user.o365_id or str(current_user.id),
    )

@router.get("/", response_model=List[TimeLogResponse])
def read_timelogs(
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    issue_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(allow_authenticated),
    db: Session = Depends(get_db)
):
    try:
        return timelog_service.get_timelogs(
            db,
            skip=skip,
            limit=limit,
            project_id=project_id,
            task_id=task_id,
            issue_id=issue_id,
            current_user=current_user if is_employee_only(current_user) else None
        )
    except Exception as e:
        import traceback
        print(f"[TIMELOG ERROR] Error in read_timelogs: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Timelog Error: {str(e)}")

@router.get("/{timelog_id}", response_model=TimeLogResponse)
def read_timelog(
    timelog_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    db_timelog = timelog_service.get_timelog(db, timelog_id=timelog_id)
    if db_timelog is None:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    if is_employee_only(current_user) and db_timelog.user_email != current_user.email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only view your own time logs.",
        )
    return db_timelog

@router.put("/{timelog_id}", response_model=TimeLogResponse)
def update_timelog(
    timelog_id: int,
    timelog: TimeLogUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    db_timelog = timelog_service.get_timelog(db, timelog_id=timelog_id)
    if db_timelog is None:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    if is_employee_only(current_user) and db_timelog.user_email != current_user.email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only update your own time logs.",
        )
    updated = timelog_service.update_timelog(
        db,
        timelog_id=timelog_id,
        timelog_update=timelog,
        actor_id=current_user.o365_id or str(current_user.id),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    return updated

@router.delete("/{timelog_id}", dependencies=[Depends(allow_team_lead_plus)])
def delete_timelog(
    timelog_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(allow_team_lead_plus),
):

    success = timelog_service.delete_timelog(
        db,
        timelog_id=timelog_id,
        actor_id=current_user.o365_id or str(current_user.id),
    )
    if not success:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    return {"message": "TimeLog deleted successfully"}

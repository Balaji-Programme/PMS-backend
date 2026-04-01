from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import allow_authenticated, allow_team_lead_plus, is_employee_only
from app.core.dependencies import auto_populate_timelog
from app.schemas.timelog import TimeLogCreate, TimeLogUpdate, TimeLogResponse
from app.services import timelog_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])


@router.post("/", response_model=TimeLogResponse)
def create_timelog(
    timelog: TimeLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    """
    All roles can create a time log.
    - `user_email` is automatically populated from the authenticated user's JWT
      via `auto_populate_timelog()` — client input is ignored for Employees.
    - Employees may only log time for themselves; the field is force-overridden.
    """
    # Centralized dependency: auto-fill user_email from token
    auto_populate_timelog(timelog, current_user)
    # Hard enforcement for Employee role
    if is_employee_only(current_user):
        timelog.user_email = current_user.email

    return timelog_service.create_timelog(
        db=db,
        timelog=timelog,
        actor_id=current_user.o365_id or str(current_user.id),
    )


@router.get("/", response_model=List[TimeLogResponse])
def read_timelogs(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    user_email: List[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    """Employees only see their own time logs."""
    if is_employee_only(current_user):
        user_email = [current_user.email]

    return timelog_service.get_timelogs(
        db,
        skip=skip,
        limit=limit,
        project_id=project_id,
        user_emails=user_email,
    )


@router.get("/{timelog_id}", response_model=TimeLogResponse)
def read_timelog(
    timelog_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    db_timelog = timelog_service.get_timelog(db, timelog_id=timelog_id)
    if db_timelog is None:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    # Employee can only view their own time logs
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
    """Only Team Lead and above can delete time logs."""
    success = timelog_service.delete_timelog(
        db,
        timelog_id=timelog_id,
        actor_id=current_user.o365_id or str(current_user.id),
    )
    if not success:
        raise HTTPException(status_code=404, detail="TimeLog not found")
    return {"message": "TimeLog deleted successfully"}

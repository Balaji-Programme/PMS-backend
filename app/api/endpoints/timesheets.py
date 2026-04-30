from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_sync_db
from app.core.security import allow_authenticated, allow_team_lead_plus, is_employee_only
from app.schemas.timesheet import TimesheetCreate, TimesheetUpdate, TimesheetResponse
from app.services import timesheet_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TimesheetResponse)
def create_timesheet(timesheet: TimesheetCreate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):

    if is_employee_only(current_user):
        timesheet.user_email = current_user.email
    return timesheet_service.create_timesheet(db=db, timesheet=timesheet, actor_id=current_user.o365_id or str(current_user.id))

@router.get("/", response_model=List[TimesheetResponse])
def read_timesheets(
    skip: int = 0,
    limit: int = 100,
    project_id: int = None,
    user_email: str = None,
    db: Session = Depends(get_sync_db),
    current_user = Depends(allow_authenticated)
):

    if is_employee_only(current_user):
        user_email = current_user.email
    return timesheet_service.get_timesheets(db, skip=skip, limit=limit, project_id=project_id, user_email=user_email)

@router.get("/{timesheet_id}", response_model=TimesheetResponse)
def read_timesheet(timesheet_id: int, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    db_timesheet = timesheet_service.get_timesheet(db, timesheet_id=timesheet_id)
    if db_timesheet is None:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if is_employee_only(current_user) and db_timesheet.user_email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied: you can only view your own timesheets.")
    return db_timesheet

@router.put("/{timesheet_id}", response_model=TimesheetResponse)
def update_timesheet(timesheet_id: int, timesheet: TimesheetUpdate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    db_timesheet = timesheet_service.get_timesheet(db, timesheet_id=timesheet_id)
    if db_timesheet is None:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if is_employee_only(current_user) and db_timesheet.user_email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied: you can only update your own timesheets.")

    updated = timesheet_service.update_timesheet(db, timesheet_id=timesheet_id, timesheet_update=timesheet, actor_id=current_user.o365_id or str(current_user.id))
    if updated is None:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    return updated

@router.delete("/{timesheet_id}", status_code=204, dependencies=[Depends(allow_team_lead_plus)])
def delete_timesheet(timesheet_id: int, db: Session = Depends(get_sync_db), current_user = Depends(allow_team_lead_plus)):
    success = timesheet_service.delete_timesheet(db, timesheet_id=timesheet_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Timesheet not found")

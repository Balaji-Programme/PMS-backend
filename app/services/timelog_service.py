from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import or_
from app.models.timelog import TimeLog
from app.models.task import Task
from app.schemas.timelog import TimeLogCreate, TimeLogUpdate
from app.utils.audit_utils import write_audit, capture_audit_details

def get_timelog(db: Session, timelog_id: int):
    return db.query(TimeLog).options(
        joinedload(TimeLog.user),
        joinedload(TimeLog.project),
        joinedload(TimeLog.task).joinedload(Task.project),
        joinedload(TimeLog.issue)
    ).filter(TimeLog.id == timelog_id).first()

def get_timelogs(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    project_id: Optional[int] = None,
    user_emails: Optional[List[str]] = None
):
    query = db.query(TimeLog)
    if project_id is not None:
        query = query.outerjoin(TimeLog.task).filter(
            or_(
                TimeLog.project_id == project_id,
                Task.project_id == project_id
            )
        ).options(contains_eager(TimeLog.task))
    else:
        query = query.options(joinedload(TimeLog.task))
        
    query = query.options(
        joinedload(TimeLog.user),
        joinedload(TimeLog.project),
        joinedload(TimeLog.issue)
    )
    if user_emails:
        query = query.filter(TimeLog.user_email.in_(user_emails))
        
    return query.offset(skip).limit(limit).all()

def create_timelog(db: Session, timelog: TimeLogCreate, actor_id: Optional[str] = None):
    db_timelog = TimeLog(
        user_email=timelog.user_email,
        project_id=timelog.project_id,
        task_id=timelog.task_id,
        issue_id=timelog.issue_id,
        timesheet_id=timelog.timesheet_id,
        date=timelog.date,
        hours=timelog.hours,
        description=timelog.description,
        log_title=timelog.log_title,
        billing_type=timelog.billing_type,
        approval_status=timelog.approval_status,
        general_log=timelog.general_log
    )
    db.add(db_timelog)
    db.flush()

    write_audit(db, actor_id, "CREATE", "timelogs",
                resource_id=timelog.project_id or db_timelog.id,
                record_id=db_timelog.id,
                details=[{
                    "field_name": "hours",
                    "old_value": None,
                    "new_value": f"{timelog.hours}h on {timelog.date} — {timelog.log_title or timelog.description or ''}"
                }])

    db.commit()
    db.refresh(db_timelog)
    return get_timelog(db, db_timelog.id)

def update_timelog(db: Session, timelog_id: int, timelog_update: TimeLogUpdate, actor_id: Optional[str] = None):
    db_timelog = db.query(TimeLog).filter(TimeLog.id == timelog_id).first()
    if not db_timelog:
        return None
    
    update_data = timelog_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_timelog, update_data)

    for key, value in update_data.items():
        setattr(db_timelog, key, value)

    write_audit(db, actor_id, "UPDATE", "timelogs",
                resource_id=db_timelog.project_id or timelog_id,
                record_id=timelog_id,
                details=changes)
        
    db.commit()
    db.refresh(db_timelog)
    return get_timelog(db, db_timelog.id)

def delete_timelog(db: Session, timelog_id: int, actor_id: Optional[str] = None):
    db_timelog = db.query(TimeLog).filter(TimeLog.id == timelog_id).first()
    if db_timelog:
        write_audit(db, actor_id, "DELETE", "timelogs",
                    resource_id=db_timelog.project_id or timelog_id,
                    record_id=timelog_id,
                    details=[{"field_name": "hours", "old_value": str(db_timelog.hours), "new_value": None}])
        db.delete(db_timelog)
        db.commit()
        return True
    return False

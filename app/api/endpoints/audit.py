from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import allow_pm
from app.models.audit import AuditLogs
from app.schemas.audit import AuditLogResponse

router = APIRouter(dependencies=[Depends(allow_pm)])

@router.get("/", response_model=List[AuditLogResponse])
def read_audit_logs(
    skip: int = 0,
    limit: int = 100,
    resource_name: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLogs)
    if resource_name:
        query = query.filter(AuditLogs.TableName == resource_name)
    if user_id:
        query = query.filter(AuditLogs.PerformedBy == user_id)

    return query.order_by(AuditLogs.PerformedOn.desc()).offset(skip).limit(limit).all()

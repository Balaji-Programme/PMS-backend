from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserBase

class TimeLogCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_title: Optional[str] = None
    
    project_id: Optional[int] = None
    task_id: Optional[int]    = None
    issue_id: Optional[int]   = None

    date: date
    daily_log_hours: float
    time_period: Optional[str] = None
    notes: Optional[str] = None

    billing_type: Optional[str] = "Billable"
    approval_status: Optional[str] = "Pending"
    general_log: Optional[bool] = False

class TimeLogUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_title: Optional[str] = None
    date: Optional[date] = None
    daily_log_hours: Optional[float] = None
    time_period: Optional[str] = None
    notes: Optional[str] = None
    billing_type: Optional[str] = None
    approval_status: Optional[str] = None

class TimeLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_title: Optional[str]
    
    user_id: int
    created_by_id: Optional[int]
    
    project_id: Optional[int]
    task_id: Optional[int]
    issue_id: Optional[int]

    date: date
    daily_log_hours: float
    time_period: Optional[str]
    notes: Optional[str]

    billing_type: str
    approval_status: str
    general_log: bool

    user: Optional[UserBase] = None
    created_by: Optional[UserBase] = None

class TimeLogBulkCreate(BaseModel):
    logs: List[TimeLogCreate]

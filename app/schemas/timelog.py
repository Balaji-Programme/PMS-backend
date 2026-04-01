from pydantic import BaseModel
from typing import Optional
import datetime
from .user import UserBase
from .task import TaskBase
from .project import ProjectBase
from .issue import IssueBase

class TimeLogBase(BaseModel):
    date: datetime.date
    hours: float
    description: Optional[str] = None
    log_title: Optional[str] = None
    billing_type: Optional[str] = "Billable"
    approval_status: Optional[str] = "Pending"
    general_log: Optional[bool] = False

class TimeLogCreate(TimeLogBase):
    user_email: Optional[str] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    issue_id: Optional[int] = None
    timesheet_id: Optional[int] = None

class TimeLogUpdate(BaseModel):
    date: Optional[datetime.date] = None
    hours: Optional[float] = None
    description: Optional[str] = None
    log_title: Optional[str] = None
    billing_type: Optional[str] = None
    approval_status: Optional[str] = None
    general_log: Optional[bool] = None
    user_email: Optional[str] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    issue_id: Optional[int] = None
    timesheet_id: Optional[int] = None

class TimeLogResponse(TimeLogBase):
    id: int
    user_email: str
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    issue_id: Optional[int] = None

    user: Optional[UserBase] = None
    project: Optional[ProjectBase] = None
    task: Optional[TaskBase] = None
    issue: Optional[IssueBase] = None

    model_config = {"from_attributes": True}

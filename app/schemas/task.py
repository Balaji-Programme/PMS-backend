from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime
from .masters import MasterResponse
from .user import UserBase
from .project import ProjectBase

TASK_STATUS_CHOICES = [
    "Open", "In Progress", "In Review", "To Be Tested", "Completed", "On Hold", "Closed"
]

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    progress: int = 0

    estimated_hours: Optional[float] = 0.0
    actual_hours: Optional[float] = 0.0
    billing_type: Optional[str] = "Billable"

    project: Optional[ProjectBase] = None

class TaskCreate(TaskBase):
    project_id: Optional[int] = None
    task_list_id: Optional[int] = None
    assignee_email: Optional[str] = None
    assignee_ids: Optional[List[int]] = []
    owner_ids: Optional[List[int]] = []
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    created_by_email: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task title must not be empty")
        return v.strip()

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    project_id: Optional[int] = None
    task_list_id: Optional[int] = None
    assignee_email: Optional[str] = None
    assignee_ids: Optional[List[int]] = None
    owner_ids: Optional[List[int]] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    public_id: str
    project_id: Optional[int] = None
    task_list_id: Optional[int] = None
    assignee_email: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    project: Optional[ProjectBase] = None
    assignee: Optional[UserBase] = None
    assignees: Optional[List[UserBase]] = []
    owners: Optional[List[UserBase]] = []
    status: Optional[MasterResponse] = None
    priority: Optional[MasterResponse] = None

    model_config = {"from_attributes": True}

class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]

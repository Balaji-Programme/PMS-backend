from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date
from .masters import MasterResponse
from .user import UserBase
from .team import TeamBase
from .project_group import ProjectGroupResponse

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client: Optional[str] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estimated_hours: Optional[float] = None

    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    actual_hours: Optional[float] = None

    model_config = {"from_attributes": True}

class ProjectCreate(ProjectBase):
    manager_email: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    is_archived: bool = False
    is_template: bool = False
    is_group: bool = False
    user_emails: Optional[List[str]] = []

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Project name must not be empty")
        return v.strip()

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    actual_hours: Optional[float] = None
    manager_email: Optional[str] = None
    status_id: Optional[int] = None
    previous_status: Optional[int] = None
    priority_id: Optional[int] = None
    is_archived: Optional[bool] = None
    is_template: Optional[bool] = None
    is_group: Optional[bool] = None
    user_emails: Optional[List[str]] = None

class ProjectResponse(BaseModel):
    id: int
    public_id: str
    name: str
    description: Optional[str] = None
    client: Optional[str] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estimated_hours: Optional[float] = None

    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    actual_hours: Optional[float] = None

    is_archived: bool = False
    is_template: bool = False
    is_group: bool = False

    manager_email: Optional[str] = None
    created_by_email: Optional[str] = None
    status_id: Optional[int] = None
    previous_status: Optional[int] = None
    priority_id: Optional[int] = None

    manager: Optional[UserBase] = None
    creator: Optional[UserBase] = None
    status: Optional[MasterResponse] = None
    previous_status_obj: Optional[MasterResponse] = None
    priority: Optional[MasterResponse] = None
    users: List[UserBase] = []

    model_config = {"from_attributes": True}

class ProjectListResponse(BaseModel):
    total: int
    items: List[ProjectResponse]

class ProjectUserCreate(BaseModel):

    user_id: str
    user_email: str
    display_name: Optional[str] = None
    project_id: int
    role_id: Optional[int] = None

    @field_validator("project_id")
    @classmethod
    def id_must_be_positive(cls, v: int, info) -> int:
        if v is None or v <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer")
        return v

    @field_validator("user_id", "user_email")
    @classmethod
    def value_must_not_be_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be null or empty")
        return v.strip()

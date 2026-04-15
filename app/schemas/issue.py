from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBase
from app.schemas.masters import MasterLookupResponse


class IssueCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bug_name: str = Field(..., min_length=1)
    description: Optional[str] = None

    project_id: Optional[int] = None
    milestone_id: Optional[int] = None
    associated_team_id: Optional[int] = None
    assignee_id: Optional[int] = None
    reporter_id: Optional[int] = None

    status_id: Optional[int] = None
    severity_id: Optional[int] = None
    classification_id: Optional[int] = None
    reporter_email: Optional[str] = None
    follower_emails: List[str] = Field(default_factory=list)
    assignee_emails: List[str] = Field(default_factory=list)

    module: Optional[str] = None
    tags: Optional[str] = None
    flag: Optional[str] = None
    reproducible_flag: bool = True

    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None


class IssueUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bug_name: Optional[str] = None
    description: Optional[str] = None

    associated_team_id: Optional[int] = None
    milestone_id: Optional[int] = None
    assignee_id: Optional[int] = None
    reporter_id: Optional[int] = None

    status_id: Optional[int] = None
    severity_id: Optional[int] = None
    classification_id: Optional[int] = None

    module: Optional[str] = None
    tags: Optional[str] = None
    flag: Optional[str] = None
    reproducible_flag: Optional[bool] = None

    start_date: Optional[date] = None
    due_date: Optional[date] = None
    last_closed_time: Optional[datetime] = None
    last_modified_time: Optional[datetime] = None
    estimated_hours: Optional[float] = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    bug_name: str
    description: Optional[str]

    project_id: Optional[int]
    milestone_id: Optional[int] = None
    associated_team_id: Optional[int]
    assignee_id: Optional[int]
    reporter_id: Optional[int]

    status_id: Optional[int] = None
    severity_id: Optional[int] = None
    classification_id: Optional[int] = None

    status_master: Optional[MasterLookupResponse] = None
    severity_master: Optional[MasterLookupResponse] = None
    classification_master: Optional[MasterLookupResponse] = None
    status: Optional[dict] = None
    severity: Optional[dict] = None
    classification: Optional[dict] = None

    module: Optional[str]
    tags: Optional[str]
    flag: Optional[str] = None
    reproducible_flag: bool

    start_date: Optional[date]
    due_date: Optional[date]
    last_closed_time: Optional[datetime]
    last_modified_time: Optional[datetime] = None
    estimated_hours: Optional[float]

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    assignee: Optional[UserBase] = None
    reporter: Optional[UserBase] = None

    followers: List[UserBase] = Field(default_factory=list)
    assignees: List[UserBase] = Field(default_factory=list)


class IssueListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[IssueResponse]

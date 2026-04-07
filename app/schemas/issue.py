from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import date, datetime
from .masters import MasterResponse
from .user import UserBase
from .project import ProjectBase
from .document import DocumentResponse

IssueClassification = Literal[
    "None", "Security", "Crash/Hang", "Data Loss", "Performance",
    "UI/UX Usability", "Other Bugs", "Feature (New)", "Enhancement"
]

IssueStatus = Literal[
    "Open", "In Progress", "In Review", "To Be Tested", "Re-opened", "Closed"
]

class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = 0.0

    module: Optional[str] = None
    tags: Optional[str] = None

    classification: Optional[IssueClassification] = "None"

    model_config = {"from_attributes": True}

class IssueCreate(IssueBase):
    project_id: Optional[int] = None
    reporter_email: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_ids: Optional[List[int]] = []
    follower_ids: Optional[List[int]] = []
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    document_ids: Optional[List[int]] = []

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Issue title must not be empty")
        return v.strip()

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[int] = None
    reporter_email: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_ids: Optional[List[int]] = None
    follower_ids: Optional[List[int]] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    classification: Optional[IssueClassification] = None
    module: Optional[str] = None
    tags: Optional[str] = None
    document_ids: Optional[List[int]] = []

class IssueResponse(IssueBase):
    id: int
    public_id: str
    project_id: Optional[int] = None
    reporter_email: Optional[str] = None
    assignee_email: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    project: Optional[ProjectBase] = None
    reporter: Optional[UserBase] = None
    assignee: Optional[UserBase] = None
    assignees: Optional[List[UserBase]] = []
    followers: Optional[List[UserBase]] = []
    status: Optional[MasterResponse] = None
    priority: Optional[MasterResponse] = None
    documents: Optional[List[DocumentResponse]] = []

    model_config = {"from_attributes": True}

class IssueListResponse(BaseModel):
    total: int
    items: List[IssueResponse]

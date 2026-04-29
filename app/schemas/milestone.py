from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserBase
from app.schemas.masters import MasterResponse, MasterLookupResponse


class MilestoneCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    milestone_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    
    project_id: Optional[int] = None
    owner_id: Optional[int]   = None

    status_id: Optional[int]   = None
    priority_id: Optional[int] = None

    flags: Optional[str]  = None
    tags: Optional[str]   = None


    start_date: Optional[date] = None
    end_date: Optional[date]   = None
    completion_percentage: Optional[int] = 0

class MilestoneUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    milestone_name: Optional[str] = None
    description: Optional[str]    = None
    owner_id: Optional[int]       = None
    status_id: Optional[int]      = None
    priority_id: Optional[int]    = None

    flags: Optional[str]          = None
    tags: Optional[str]           = None

    start_date: Optional[date]    = None
    end_date: Optional[date]      = None
    completion_percentage: Optional[int] = None

    previous_status_id: Optional[int]   = None

    is_processed: Optional[bool]        = None


class ProjectMin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str
    customer_name: Optional[str] = None
    account_name: Optional[str] = None

class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    milestone_name: str
    description: Optional[str]

    project_id: Optional[int]
    project: Optional[ProjectMin] = None
    owner_id: Optional[int]

    status_id: Optional[int]
    priority_id: Optional[int] = None

    status: Optional[dict] = None
    priority: Optional[dict] = None
    flags: Optional[str]
    tags: Optional[str]

    status_master: Optional[MasterLookupResponse]     = None
    priority_master: Optional[MasterLookupResponse]   = None


    start_date: Optional[date]
    end_date: Optional[date]
    completion_percentage: Optional[int]

    is_processed: bool              = False
    previous_status_id: Optional[int] = None



    task_count: int = 0
    issue_count: int = 0

    owner: Optional[UserBase] = None

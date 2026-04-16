from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserBase

class MilestoneCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    milestone_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    
    project_id: Optional[int] = None
    owner_id: Optional[int]   = None

    status: Optional[str] = None
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
    status: Optional[str]         = None
    flags: Optional[str]          = None
    tags: Optional[str]           = None
    start_date: Optional[date]    = None
    end_date: Optional[date]      = None
    completion_percentage: Optional[int] = None

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

    status: Optional[str]
    flags: Optional[str]
    tags: Optional[str]

    start_date: Optional[date]
    end_date: Optional[date]
    completion_percentage: Optional[int]

    task_count: int = 0
    issue_count: int = 0

    owner: Optional[UserBase] = None

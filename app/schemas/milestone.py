from pydantic import BaseModel
from typing import Optional
from datetime import date
from .masters import MasterResponse
from .project import ProjectBase

class MilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class MilestoneCreate(MilestoneBase):
    project_id: int
    owner_email: str | None = None
    flags: str | None = None
    tags: str | None = None

class MilestoneUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    project_id: int | None = None
    owner_email: str | None = None
    flags: str | None = None
    tags: str | None = None

class MilestoneOwnerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    
    class Config:
        from_attributes = True

class MilestoneResponse(MilestoneBase):
    id: int
    public_id: str
    project_id: int | None = None
    owner_email: str | None = None
    flags: str | None = None
    tags: str | None = None

    project: ProjectBase | None = None
    owner: MilestoneOwnerResponse | None = None

    model_config = {"from_attributes": True}

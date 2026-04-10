from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

class TemplateTaskCreate(BaseModel):
    title: str               = Field(..., min_length=1, max_length=255)
    description: Optional[str]    = None
    estimated_hours: Optional[float] = None
    priority_id: Optional[int]    = None
    order_index: int              = 0

    model_config = ConfigDict(from_attributes=True)

class TemplateTaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]    = None
    estimated_hours: Optional[float] = None
    priority_id: Optional[int]    = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)

class ProjectTemplateCreate(BaseModel):
    name: str               = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tasks: List[TemplateTaskCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ProjectTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]          = None
    tasks: List[TemplateTaskResponse]   = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

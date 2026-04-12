from pydantic import BaseModel
from typing import Optional, Any

class TaskListBase(BaseModel):
    name: str
    description: Optional[str] = None

class TaskListCreate(TaskListBase):
    project_id: int

class TaskListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[int] = None

class TaskListResponse(TaskListBase):
    id: int
    project_id: int
    project: Optional[Any] = None

    model_config = {"from_attributes": True}

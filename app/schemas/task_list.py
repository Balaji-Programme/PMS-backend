from pydantic import BaseModel
from typing import Optional

class TaskListBase(BaseModel):
    name: str
    description: Optional[str] = None

class TaskListCreate(TaskListBase):
    project_id: int

class TaskListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[int] = None

class ProjectMin(BaseModel):
    id: int
    project_name: str
    customer_name: Optional[str] = None
    account_name: Optional[str] = None

    model_config = {"from_attributes": True}

class TaskListResponse(TaskListBase):
    id: int
    project_id: int
    project: Optional[ProjectMin] = None

    model_config = {"from_attributes": True}

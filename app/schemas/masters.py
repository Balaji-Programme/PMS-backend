from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class MasterBase(BaseModel):
    name: str

class MasterCreate(MasterBase):
    pass

class MasterResponse(MasterBase):
    id: int

    model_config = {"from_attributes": True}

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Dict[str, Any] = {}

class RoleCreate(RoleBase):
    user_ids: Optional[List[int]] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    user_ids: Optional[List[int]] = None

class RoleResponse(RoleBase):
    id: int
    users_count: Optional[int] = None

    model_config = {"from_attributes": True}

class SkillBase(BaseModel):
    name: str

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int

    model_config = {"from_attributes": True}

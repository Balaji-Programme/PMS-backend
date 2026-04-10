from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import BillingModel, ProjectType
from app.schemas.user import UserBase
from app.schemas.masters import MasterResponse

class ProjectCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_name: str       = Field(..., min_length=1)
    project_name: str       = Field(..., min_length=1)
    customer_name: str      = Field(..., min_length=1)
    project_id_sync: str    = Field(..., min_length=1)
    
    billing_model: BillingModel
    project_type: ProjectType
    
    expected_start_date: Optional[date] = None
    expected_end_date: Optional[date]   = None

    client_name: Optional[str]              = None
    description: Optional[str]              = None
    project_status_external: Optional[str]  = None
    
    owner_id: Optional[int]                 = None
    project_manager_id: Optional[int]       = None
    delivery_head_id: Optional[int]         = None
    template_id: Optional[int]              = None
    
    status: Optional[str]                   = "Active"
    priority: Optional[str]                 = "Medium"

    estimated_hours: Optional[float]        = 0.0
    actual_hours: Optional[float]           = 0.0
    
    actual_start_date: Optional[date]       = None
    actual_end_date: Optional[date]         = None

    is_archived: bool                       = False
    is_template: bool                       = False
    is_group: bool                          = False

    user_emails: List[str]                  = Field(default_factory=list)

class ProjectUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_name: Optional[str]       = None
    project_name: Optional[str]       = None
    customer_name: Optional[str]      = None
    client_name: Optional[str]        = None
    
    billing_model: Optional[BillingModel]   = None
    project_type: Optional[ProjectType]     = None
    project_status_external: Optional[str]  = None
    
    expected_start_date: Optional[date] = None
    expected_end_date: Optional[date]   = None
    
    owner_id: Optional[int]                 = None
    project_manager_id: Optional[int]       = None
    delivery_head_id: Optional[int]         = None
    
    status: Optional[str]                   = None
    priority: Optional[str]                 = None
    description: Optional[str]              = None

    estimated_hours: Optional[float]        = None
    actual_hours: Optional[float]           = None
    actual_start_date: Optional[date]       = None
    actual_end_date: Optional[date]         = None
    
    is_archived: Optional[bool]             = None
    is_template: Optional[bool]             = None
    is_group: Optional[bool]                = None
    user_emails: Optional[List[str]]        = None

class ProjectSyncUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id_sync: Optional[str] = None
    account_name: Optional[str]    = None
    customer_name: Optional[str]   = None
    project_name: Optional[str]    = None

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    project_id_sync: str
    account_name: str
    project_name: str
    customer_name: str
    client_name: Optional[str] = None

    billing_model: BillingModel
    project_type: ProjectType
    project_status_external: Optional[str] = None
    
    expected_start_date: Optional[date] = None
    expected_end_date: Optional[date]   = None

    description: Optional[str]          = None
    status: str                         = "Active"
    priority: str                       = "Medium"

    owner_id: Optional[int]             = None
    project_manager_id: Optional[int]   = None
    delivery_head_id: Optional[int]     = None
    template_id: Optional[int]          = None

    estimated_hours: Optional[float]    = 0.0
    actual_hours: Optional[float]       = 0.0
    actual_start_date: Optional[date]   = None
    actual_end_date: Optional[date]     = None

    is_archived: bool                   = False
    is_template: bool                   = False
    is_group: bool                      = False
    is_processed: bool                  = False

    owner: Optional[UserBase]           = None
    project_manager: Optional[UserBase] = None
    delivery_head: Optional[UserBase]   = None

class ProjectListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[ProjectResponse]

class ProjectUserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    user_email: str
    display_name: Optional[str]   = None
    project_id: int
    project_profile: str          = "Member"
    portal_profile: str           = "User"

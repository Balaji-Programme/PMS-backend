from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict
from .base import BaseSchema

class AuditDetailCreate(BaseModel):
    field_name: str = Field(alias="FieldName")
    old_value: Optional[str] = Field(None, alias="OldValue")
    new_value: Optional[str] = Field(None, alias="NewValue")

class AuditDetailResponse(BaseModel):
    id: int = Field(alias="Id")
    audit_log_id: int = Field(alias="AuditLogId")
    field_name: str = Field(alias="FieldName")
    old_value: Optional[str] = Field(None, alias="OldValue")
    new_value: Optional[str] = Field(None, alias="NewValue")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class AuditLogCreate(BaseModel):
    table_name: str = Field(alias="TableName")
    action: int = Field(alias="Action")
    performed_by: uuid.UUID = Field(alias="PerformedBy")

class AuditLogResponse(BaseSchema):
    id: int = Field(alias="ID")
    action_type: int = Field(alias="Action")
    resource_name: str = Field(alias="TableName")
    user_id: uuid.UUID = Field(alias="PerformedBy")
    created_at: datetime = Field(alias="PerformedOn")
    details: List[AuditDetailResponse] = []

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

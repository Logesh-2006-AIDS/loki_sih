import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    application_id: Optional[uuid.UUID] = None
    entity_type: str
    entity_id: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    details: Dict[str, Any] = {}


class AuditLogCreate(AuditLogBase):
    actor_id: Optional[uuid.UUID] = None


class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

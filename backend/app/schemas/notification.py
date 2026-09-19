import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.core.enums import NotificationChannel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    application_id: Optional[uuid.UUID] = None
    channel: NotificationChannel
    title: str
    message: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

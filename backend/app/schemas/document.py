import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.core.enums import DocumentStatus


class DocumentBase(BaseModel):
    document_type: str
    original_filename: str
    mime_type: str
    file_size: int


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    application_id: uuid.UUID
    status: DocumentStatus
    uploaded_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

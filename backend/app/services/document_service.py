import uuid
from typing import BinaryIO, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.enums import DocumentStatus
from app.core.status_transitions import can_transition_document
from app.core.exceptions import (
    EntityNotFoundException,
    InvalidStatusTransitionException,
)
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.storage_service import BaseStorageService, LocalStorageService
from app.repositories.audit_repo import AuditRepository


class DocumentService:
    """
    Document management service for storing uploaded files, tracking
    verification states, and recording entity-level audit logs.
    """

    def __init__(
        self, db: Session, storage_service: Optional[BaseStorageService] = None
    ):
        self.db = db
        self.storage = storage_service or LocalStorageService()
        self.audit_repo = AuditRepository(db)

    def upload_document(
        self,
        application_id: uuid.UUID,
        document_type: str,
        filename: str,
        mime_type: str,
        file_size: int,
        file_obj: BinaryIO,
        actor_id: Optional[uuid.UUID] = None,
    ) -> DocumentResponse:
        subfolder = f"applications/{application_id}"
        storage_path = self.storage.save_file(
            file_obj=file_obj, filename=filename, subfolder=subfolder
        )

        doc = Document(
            application_id=application_id,
            document_type=document_type,
            original_filename=filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=file_size,
            status=DocumentStatus.PENDING,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        self.audit_repo.log_event(
            entity_type="DOCUMENT",
            entity_id=str(doc.id),
            application_id=application_id,
            actor_id=actor_id,
            action="DOCUMENT_UPLOADED",
            new_status=str(DocumentStatus.PENDING.value),
            details={
                "document_type": document_type,
                "original_filename": filename,
                "file_size": file_size,
            },
        )
        return DocumentResponse.model_validate(doc)

    def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")
        return DocumentResponse.model_validate(doc)

    def list_by_application(self, application_id: uuid.UUID) -> List[DocumentResponse]:
        query = select(Document).where(Document.application_id == application_id)
        docs = self.db.execute(query).scalars().all()
        return [DocumentResponse.model_validate(d) for d in docs]

    def update_status(
        self,
        document_id: uuid.UUID,
        new_status: DocumentStatus,
        actor_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
    ) -> DocumentResponse:
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")

        prev_status = doc.status
        if prev_status != new_status:
            if not can_transition_document(prev_status, new_status):
                raise InvalidStatusTransitionException(
                    "DOCUMENT", str(prev_status), str(new_status)
                )
            doc.status = new_status
            self.db.commit()
            self.db.refresh(doc)

            self.audit_repo.log_event(
                entity_type="DOCUMENT",
                entity_id=str(doc.id),
                application_id=doc.application_id,
                actor_id=actor_id,
                action="DOCUMENT_STATUS_UPDATED",
                previous_status=str(prev_status.value if hasattr(prev_status, "value") else prev_status),
                new_status=str(new_status.value if hasattr(new_status, "value") else new_status),
                details={"reason": reason} if reason else None,
            )

        return DocumentResponse.model_validate(doc)

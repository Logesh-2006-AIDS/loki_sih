import uuid
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.enums import DocumentStatus, ApplicationStatus
from app.core.status_transitions import can_transition_document
from app.core.exceptions import (
    EntityNotFoundException,
    InvalidStatusTransitionException,
    ForbiddenException,
    ValidationException,
)
from app.models.document import Document
from app.models.application import Application
from app.schemas.document import DocumentResponse
from app.services.storage_service import BaseStorageService, LocalStorageService
from app.services.file_validator import validate_file
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
        file_obj: BinaryIO,
        actor_id: Optional[uuid.UUID] = None,
        allowed_extensions: Optional[List[str]] = None,
        max_size_bytes: int = 5 * 1024 * 1024,
        allow_multiple: bool = False,
    ) -> DocumentResponse:
        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        # Immutability check: Only DRAFT applications can receive uploaded documents
        if app.status != ApplicationStatus.DRAFT:
            raise ForbiddenException("Cannot upload documents to an application that has already been submitted.")

        # 1. Validate file (magic bytes, size, extension, filename safety)
        clean_filename, verified_mime, file_size = validate_file(
            file_obj=file_obj,
            filename=filename,
            allowed_extensions=allowed_extensions,
            max_size_bytes=max_size_bytes,
        )

        # 2. Check for duplicate/existing document under the same document_type
        existing_doc = (
            self.db.execute(
                select(Document).where(
                    Document.application_id == application_id,
                    Document.document_type == document_type,
                )
            )
            .scalars()
            .first()
        )

        subfolder = f"applications/{application_id}"
        # 3. Save physical file to storage
        storage_path = self.storage.save_file(
            file_obj=file_obj, filename=clean_filename, subfolder=subfolder
        )

        # 4. Save to Database with rollback cleanup
        try:
            if existing_doc and not allow_multiple:
                # Replace existing document
                old_storage_path = existing_doc.storage_path
                existing_doc.original_filename = clean_filename
                existing_doc.storage_path = storage_path
                existing_doc.mime_type = verified_mime
                existing_doc.file_size = file_size
                existing_doc.status = DocumentStatus.UPLOADED
                doc = existing_doc

                # Delete old file from storage
                if old_storage_path and old_storage_path != storage_path:
                    self.storage.delete_file(old_storage_path)

                action = "DOCUMENT_REPLACED"
            else:
                doc = Document(
                    application_id=application_id,
                    document_type=document_type,
                    original_filename=clean_filename,
                    storage_path=storage_path,
                    mime_type=verified_mime,
                    file_size=file_size,
                    status=DocumentStatus.UPLOADED,
                )
                self.db.add(doc)
                action = "DOCUMENT_UPLOADED"

            self.db.commit()
            self.db.refresh(doc)

            self.audit_repo.log_event(
                entity_type="DOCUMENT",
                entity_id=str(doc.id),
                application_id=application_id,
                actor_id=actor_id,
                action=action,
                new_status=str(DocumentStatus.UPLOADED.value),
                details={
                    "document_type": document_type,
                    "original_filename": clean_filename,
                    "file_size": file_size,
                    "mime_type": verified_mime,
                },
            )
            return DocumentResponse.model_validate(doc)

        except Exception as e:
            # Transactional cleanup: remove physical file if DB insert fails
            self.storage.delete_file(storage_path)
            self.db.rollback()
            raise e

    def delete_document(
        self, document_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None
    ) -> None:
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")

        app = self.db.get(Application, doc.application_id)
        if not app:
            raise EntityNotFoundException("Parent application not found")

        # Immutability check: Only DRAFT documents can be deleted
        if app.status != ApplicationStatus.DRAFT:
            raise ForbiddenException("Cannot delete documents from an application that has been submitted.")

        # Log audit event BEFORE deleting record so reference is captured
        self.audit_repo.log_event(
            entity_type="DOCUMENT",
            entity_id=str(doc.id),
            application_id=doc.application_id,
            actor_id=actor_id,
            action="DOCUMENT_DELETED",
            previous_status=str(doc.status.value if hasattr(doc.status, "value") else doc.status),
            details={
                "document_type": doc.document_type,
                "original_filename": doc.original_filename,
            },
        )

        # Delete physical file from storage
        self.storage.delete_file(doc.storage_path)

        # Delete database record
        self.db.delete(doc)
        self.db.commit()

    def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")
        return DocumentResponse.model_validate(doc)

    def get_document_file(self, document_id: uuid.UUID) -> Tuple[Path, str, str]:
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")

        file_path = self.storage.get_file_path(doc.storage_path)
        if not file_path.exists() or not file_path.is_file():
            raise EntityNotFoundException("Document file not found in storage")

        return file_path, doc.original_filename, doc.mime_type

    def list_by_application(self, application_id: uuid.UUID) -> List[DocumentResponse]:
        query = select(Document).where(Document.application_id == application_id).order_by(Document.uploaded_at.asc())
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

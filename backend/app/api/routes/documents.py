import uuid
from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    require_roles,
    check_officer_application_scope,
)
from app.core.enums import UserRole, DocumentStatus, ApplicationStatus
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.models.application import Application
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.repositories.scheme_version_repo import SchemeVersionRepository

router = APIRouter()


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus
    reason: str | None = None


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document for an application (legacy endpoint)",
)
def upload_document(
    application_id: uuid.UUID = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException(f"Application with ID {application_id} not found")

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot upload documents for another applicant's application")

    if app.status != ApplicationStatus.DRAFT:
        raise ForbiddenException("Cannot upload documents to an application that has already been submitted")

    # Load scheme version document configuration
    sv_repo = SchemeVersionRepository(db)
    version = None
    if app.scheme_version_id:
        version = sv_repo.get_by_id(app.scheme_version_id)
    if not version:
        version = sv_repo.get_active_version(app.scheme_id)

    allowed_extensions = None
    max_size_bytes = 5 * 1024 * 1024
    allow_multiple = False

    if version and version.required_documents:
        docs_config = version.required_documents.get("documents", [])
        for doc_cfg in docs_config:
            code = doc_cfg.get("code") or doc_cfg.get("type")
            if code == document_type:
                if doc_cfg.get("allowed_extensions"):
                    allowed_extensions = doc_cfg.get("allowed_extensions")
                if doc_cfg.get("max_size_bytes"):
                    max_size_bytes = doc_cfg.get("max_size_bytes")
                elif doc_cfg.get("max_size_mb"):
                    max_size_bytes = doc_cfg.get("max_size_mb") * 1024 * 1024
                allow_multiple = doc_cfg.get("allow_multiple", False)
                break

    service = DocumentService(db)
    filename = file.filename or "uploaded_file"

    return service.upload_document(
        application_id=application_id,
        document_type=document_type,
        filename=filename,
        file_obj=file.file,
        actor_id=current_user.id,
        allowed_extensions=allowed_extensions,
        max_size_bytes=max_size_bytes,
        allow_multiple=allow_multiple,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata by ID",
)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(db)
    doc = service.get_document(document_id)
    app = db.get(Application, doc.application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        if app and app.applicant_id != current_user.id:
            raise ForbiddenException("Cannot access document belonging to another applicant")
    elif user_role == UserRole.OFFICER:
        if app and not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this document")

    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an uploaded document (DRAFT applications only)",
)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise EntityNotFoundException(f"Document with ID {document_id} not found")

    app = db.get(Application, doc.application_id)
    if not app:
        raise EntityNotFoundException("Application not found")

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot delete document belonging to another applicant")

    if app.status != ApplicationStatus.DRAFT:
        raise ForbiddenException("Cannot delete documents from a submitted application")

    service = DocumentService(db)
    service.delete_document(document_id=document_id, actor_id=current_user.id)
    return None


@router.get(
    "/{document_id}/download",
    summary="Safely download an uploaded document without exposing filesystem paths",
)
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(db)
    doc = service.get_document(document_id)
    app = db.get(Application, doc.application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        if app and app.applicant_id != current_user.id:
            raise ForbiddenException("Cannot access document belonging to another applicant")
    elif user_role == UserRole.OFFICER:
        if app and not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this document")

    file_path, original_filename, mime_type = service.get_document_file(document_id)
    return FileResponse(
        path=str(file_path),
        filename=original_filename,
        media_type=mime_type,
    )


@router.get(
    "/application/{application_id}",
    response_model=List[DocumentResponse],
    summary="List all documents associated with an application",
)
def list_application_documents(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException(f"Application with ID {application_id} not found")

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot access documents belonging to another user")
    elif user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over documents for this application")

    service = DocumentService(db)
    return service.list_by_application(application_id)


@router.patch(
    "/{document_id}/status",
    response_model=DocumentResponse,
    summary="Update document verification status (Officer or Admin)",
)
def update_document_status(
    document_id: uuid.UUID,
    data: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = DocumentService(db)
    return service.update_status(
        document_id=document_id,
        new_status=data.status,
        actor_id=staff.id,
        reason=data.reason,
    )

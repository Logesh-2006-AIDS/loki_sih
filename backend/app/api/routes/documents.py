import uuid
from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    require_roles,
    check_officer_application_scope,
)
from app.core.enums import UserRole, DocumentStatus
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.models.application import Application
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter()


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus
    reason: str | None = None


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document for an application",
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
        raise EntityNotFoundException("Application", application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot upload documents for another applicant's application")

    service = DocumentService(db)
    filename = file.filename or "uploaded_file"
    file_size = file.size or 0
    mime_type = file.content_type or "application/octet-stream"

    return service.upload_document(
        application_id=application_id,
        document_type=document_type,
        filename=filename,
        mime_type=mime_type,
        file_size=file_size,
        file_obj=file.file,
        actor_id=current_user.id,
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
        raise EntityNotFoundException("Application", application_id)

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

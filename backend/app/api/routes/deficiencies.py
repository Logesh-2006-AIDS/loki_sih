import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.deficiency import (
    PublicDeficiencyListResponse,
    DeficiencyReplacementUploadResponse,
    ApplicationResubmitRequest,
    ApplicationResubmitResponse,
)
from app.services.deficiency_service import DeficiencyService

router = APIRouter()


@router.get(
    "/{application_id}/deficiencies",
    response_model=PublicDeficiencyListResponse,
    summary="List itemized deficiencies for an application (Applicant-safe)",
)
def get_application_deficiencies(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeficiencyService(db)
    return service.get_applicant_deficiencies(application_id=application_id, user=current_user)


@router.post(
    "/{application_id}/deficiencies/{deficiency_id}/resolve",
    response_model=DeficiencyReplacementUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a replacement document for a specific itemized deficiency",
)
def resolve_deficiency_upload(
    application_id: uuid.UUID,
    deficiency_id: uuid.UUID,
    file: UploadFile = File(...),
    applicant_remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeficiencyService(db)
    return service.upload_replacement_document(
        application_id=application_id,
        deficiency_id=deficiency_id,
        filename=file.filename or "replacement_document",
        file_obj=file.file,
        applicant_remarks=applicant_remarks,
        user=current_user,
    )


@router.post(
    "/{application_id}/resubmit",
    response_model=ApplicationResubmitResponse,
    summary="Resubmit application after all replacement documents have been uploaded",
)
def resubmit_application(
    application_id: uuid.UUID,
    data: ApplicationResubmitRequest,
    background_tasks: BackgroundTasks,
    sync_verify: bool = Query(False, description="Run AI verification synchronously for test automation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeficiencyService(db)
    return service.resubmit_application(
        application_id=application_id,
        data=data,
        user=current_user,
        background_tasks=background_tasks,
        sync_verify=sync_verify,
    )


@router.post(
    "/{application_id}/deficiencies/notify-pending",
    summary="Dispatch pending deficiency notifications for this application",
)
def notify_pending_deficiencies(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeficiencyService(db)
    dispatched = service.dispatch_pending_deficiency_notifications(application_id=application_id)
    return {"status": "SUCCESS", "dispatched_count": dispatched}

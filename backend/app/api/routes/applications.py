import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    require_roles,
    check_officer_application_scope,
)
from app.core.enums import UserRole, ApplicationStatus
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.models.application import Application
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.schemas.document import DocumentResponse
from app.schemas.verification import ApplicationVerificationSummaryResponse
from app.services.application_service import ApplicationService
from app.services.document_service import DocumentService
from app.repositories.scheme_version_repo import SchemeVersionRepository


router = APIRouter()


@router.get(
    "/",
    response_model=List[ApplicationResponse],
    summary="List applications (filtered for applicants, full queue for officers/committee/admins)",
)
def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        return service.list_by_applicant(current_user.id)
    else:
        return service.list_all(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new draft application",
)
def create_draft_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    return service.create_draft(current_user.id, data)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get application details by ID",
)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot access application belonging to another user")

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return app


@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application draft",
)
@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application draft (PATCH alias)",
)
def update_application_draft(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        if app.applicant_id != current_user.id:
            raise ForbiddenException("Cannot modify application belonging to another user")
        if data.status is not None and data.status != app.status:
            raise ForbiddenException("Applicants cannot directly modify application workflow status")
        if app.status != ApplicationStatus.DRAFT:
            raise ForbiddenException("Cannot modify submitted application")
    elif user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return service.update_application(
        application_id=application_id,
        data=data,
        actor_id=current_user.id,
    )


def _run_background_application_verification(application_id: uuid.UUID, actor_id: uuid.UUID):
    import logging
    from app.db.session import SessionLocal
    from app.services.verification_service import DocumentVerificationService

    db = SessionLocal()
    try:
        verif_service = DocumentVerificationService(db)
        verif_service.verify_application_documents(application_id, actor_id=actor_id)
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Background verification failed for application {application_id}: {e}"
        )
    finally:
        db.close()


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationResponse,
    summary="Submit a draft application",
)
def submit_application(
    application_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    sync_verify: bool = Query(False, description="Run verification synchronously in same request"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot submit application belonging to another user")

    response = service.submit_application(
        application_id=application_id,
        applicant_id=current_user.id,
        trigger_verification=sync_verify,
    )

    if not sync_verify:
        background_tasks.add_task(
            _run_background_application_verification,
            application_id,
            current_user.id,
        )

    return response



@router.post(
    "/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document for an application",
)
def upload_application_document(
    application_id: uuid.UUID,
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

    doc_service = DocumentService(db)
    return doc_service.upload_document(
        application_id=application_id,
        document_type=document_type,
        filename=file.filename or "uploaded_document",
        file_obj=file.file,
        actor_id=current_user.id,
        allowed_extensions=allowed_extensions,
        max_size_bytes=max_size_bytes,
        allow_multiple=allow_multiple,
    )


@router.get(
    "/{application_id}/documents",
    response_model=List[DocumentResponse],
    summary="List all documents uploaded for an application",
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

    doc_service = DocumentService(db)
    return doc_service.list_by_application(application_id)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status (Officer, Committee, or Admin)",
)
def update_application_status(
    application_id: uuid.UUID,
    update_data: ApplicationUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(
        require_roles([UserRole.OFFICER, UserRole.COMMITTEE, UserRole.ADMIN])
    ),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = staff.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, staff.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return service.update_application(
        application_id=application_id,
        data=update_data,
        actor_id=staff.id,
    )


@router.post(
    "/{application_id}/verify",
    response_model=ApplicationVerificationSummaryResponse,
    summary="Trigger/re-run AI verification for all application documents (Staff Only)",
)
def trigger_application_verification(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    staff: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException(f"Application with ID {application_id} not found")

    user_role = staff.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, staff.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    from app.services.verification_service import DocumentVerificationService
    verif_service = DocumentVerificationService(db)
    result = verif_service.verify_application_documents(
        application_id=application_id,
        actor_id=staff.id,
        force_rerun=True,
    )

    verifications = result["verifications"]
    verified_count = sum(1 for v in verifications if v.verification_status == "VERIFIED")
    flagged_count = sum(1 for v in verifications if v.verification_status == "FLAGGED")

    return ApplicationVerificationSummaryResponse(
        application_id=app.id,
        application_status=str(app.status.value if hasattr(app.status, "value") else app.status),
        total_documents=len(app.documents or []),
        verified_count=verified_count,
        flagged_count=flagged_count,
        document_verifications=verifications,
    )


@router.get(
    "/{application_id}/verifications",
    response_model=ApplicationVerificationSummaryResponse,
    summary="Get verification summary and evidence across all application documents (Staff Only)",
)
def get_application_verifications(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    staff: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException(f"Application with ID {application_id} not found")

    user_role = staff.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, staff.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    from app.models.document_verification import DocumentVerification
    documents = app.documents or []
    doc_ids = [d.id for d in documents]

    verifications = (
        db.query(DocumentVerification)
        .filter(DocumentVerification.document_id.in_(doc_ids))
        .all()
        if doc_ids
        else []
    )

    verified_count = sum(1 for v in verifications if v.verification_status == "VERIFIED")
    flagged_count = sum(1 for v in verifications if v.verification_status == "FLAGGED")

    return ApplicationVerificationSummaryResponse(
        application_id=app.id,
        application_status=str(app.status.value if hasattr(app.status, "value") else app.status),
        total_documents=len(documents),
        verified_count=verified_count,
        flagged_count=flagged_count,
        document_verifications=verifications,
    )


@router.get(
    "/{application_id}/result",
    summary="Get sanitized selection result for applicant",
)
def get_applicant_selection_result(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.selection_result import SelectionResult
    from app.schemas.committee import ApplicantSelectionResultResponse

    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException("APPLICATION", application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot access application belonging to another user")

    sel = (
        db.query(SelectionResult)
        .filter(SelectionResult.application_id == application_id)
        .order_by(SelectionResult.selection_round.desc(), SelectionResult.created_at.desc())
        .first()
    )

    # Only expose selection result once application has officially reached final selection status
    final_statuses = (
        ApplicationStatus.SELECTED,
        ApplicationStatus.WAITLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FELLOWSHIP_ACTIVE,
    )

    if not sel or app.status not in final_statuses:
        status_str = app.status.value if hasattr(app.status, "value") else str(app.status)
        return ApplicantSelectionResultResponse(
            application_reference_id=app.reference_id,
            result="PENDING_ANNOUNCEMENT" if status_str in ("VERIFIED", "MERIT_RANKED") else status_str,
            rank=None,
            selection_round=1,
            finalized_at=None,
        )

    return ApplicantSelectionResultResponse(
        application_reference_id=app.reference_id,
        result=sel.result.value if hasattr(sel.result, "value") else str(sel.result),
        rank=sel.rank,
        selection_round=sel.selection_round,
        finalized_at=sel.finalized_at,
    )


import uuid
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.enums import ApplicationStatus
from app.core.status_transitions import can_transition_application
from app.core.exceptions import (
    EntityNotFoundException,
    InvalidStatusTransitionException,
    ForbiddenException,
    ValidationException,
)
from app.models.application import Application
from app.models.document import Document
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.repositories.application_repo import ApplicationRepository
from app.repositories.scheme_repo import SchemeRepository
from app.repositories.scheme_version_repo import SchemeVersionRepository
from app.repositories.audit_repo import AuditRepository


class ApplicationService:
    """
    Application lifecycle management service covering draft creation,
    submission, status transitions, dynamic field validation, and audit trail generation.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ApplicationRepository(db)
        self.scheme_repo = SchemeRepository(db)
        self.scheme_version_repo = SchemeVersionRepository(db)
        self.audit_repo = AuditRepository(db)

    def _generate_reference_id(self, scheme_code: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m")
        random_suffix = secrets.token_hex(3).upper()
        return f"MTA-{scheme_code}-{timestamp}-{random_suffix}"

    def create_draft(
        self, applicant_id: uuid.UUID, data: ApplicationCreate
    ) -> ApplicationResponse:
        scheme = self.scheme_repo.get_by_id(data.scheme_id)
        if not scheme:
            raise EntityNotFoundException(f"Scheme with ID {data.scheme_id} not found")

        # Reuse existing unfinished draft if present for this applicant and scheme
        existing_draft = (
            self.db.execute(
                select(Application).where(
                    Application.applicant_id == applicant_id,
                    Application.scheme_id == data.scheme_id,
                    Application.status == ApplicationStatus.DRAFT,
                )
            )
            .scalars()
            .first()
        )
        if existing_draft:
            if data.form_data:
                existing_draft.form_data = {**existing_draft.form_data, **data.form_data}
                self.db.commit()
                self.db.refresh(existing_draft)
            return ApplicationResponse.model_validate(existing_draft)

        active_version = self.scheme_version_repo.get_active_version(scheme.id)
        ref_id = self._generate_reference_id(scheme.scheme_code)
        application = Application(
            reference_id=ref_id,
            applicant_id=applicant_id,
            scheme_id=data.scheme_id,
            scheme_version_id=active_version.id if active_version else None,
            status=ApplicationStatus.DRAFT,
            form_data=data.form_data,
        )
        created = self.repo.create(application)

        self.audit_repo.log_event(
            entity_type="APPLICATION",
            entity_id=str(created.id),
            application_id=created.id,
            actor_id=applicant_id,
            action="APPLICATION_DRAFT_CREATED",
            new_status=str(ApplicationStatus.DRAFT.value),
            details={
                "reference_id": ref_id,
                "scheme_code": scheme.scheme_code,
                "scheme_version": active_version.scheme_version if active_version else "1.0",
            },
        )
        return ApplicationResponse.model_validate(created)

    def _validate_submission_requirements(self, app: Application) -> None:
        """
        Validates that all required fields from form_schema and all required
        documents from required_documents have been provided before submission.
        """
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        if not version:
            return  # Minimal/legacy test environment with no versions

        # 1. Validate form fields
        form_schema = version.form_schema or {}
        sections = form_schema.get("sections", [])
        form_data = app.form_data or {}

        missing_fields: List[str] = []
        for section in sections:
            fields = section.get("fields", [])
            for field in fields:
                if isinstance(field, dict) and field.get("required"):
                    name = field.get("name") or field.get("id")
                    label = field.get("label") or name

                    # Check in flat or section-nested form_data
                    val = form_data.get(name)
                    if val is None and section.get("id"):
                        val = form_data.get(section["id"], {}).get(name)

                    if val is None or (isinstance(val, str) and not val.strip()) or (isinstance(val, bool) and val is False):
                        missing_fields.append(f"{label} ({name})")

        if missing_fields:
            raise ValidationException(
                f"Missing required application fields: {', '.join(missing_fields)}"
            )

        # 2. Validate required documents
        req_docs_config = version.required_documents or {}
        doc_list = req_docs_config.get("documents", [])
        if doc_list:
            # Query uploaded documents for this application
            uploaded = (
                self.db.execute(
                    select(Document).where(Document.application_id == app.id)
                )
                .scalars()
                .all()
            )
            uploaded_types = {d.document_type for d in uploaded}

            missing_docs: List[str] = []
            for doc_cfg in doc_list:
                if doc_cfg.get("required"):
                    doc_code = doc_cfg.get("code") or doc_cfg.get("type")
                    doc_label = doc_cfg.get("label") or doc_cfg.get("name") or doc_code
                    if doc_code not in uploaded_types:
                        missing_docs.append(f"{doc_label} [{doc_code}]")

            if missing_docs:
                raise ValidationException(
                    f"Missing mandatory documents: {', '.join(missing_docs)}"
                )

    def submit_application(
        self,
        application_id: uuid.UUID,
        applicant_id: uuid.UUID,
        trigger_verification: bool = False,
    ) -> ApplicationResponse:
        app = self.repo.get_by_id(application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        if app.applicant_id != applicant_id:
            raise ForbiddenException("Cannot submit application belonging to another user")

        if app.status != ApplicationStatus.DRAFT:
            raise InvalidStatusTransitionException(
                "APPLICATION", str(app.status), str(ApplicationStatus.SUBMITTED)
            )

        # 1. Validate required form fields and required documents
        self._validate_submission_requirements(app)

        # 2. Ensure scheme_version_id is bound and freeze rules snapshot
        if not app.scheme_version_id:
            active_version = self.scheme_version_repo.get_active_version(app.scheme_id)
            if active_version:
                app.scheme_version_id = active_version.id
                app.frozen_rules_snapshot = dict(active_version.eligibility_rules)
        else:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
            if version:
                app.frozen_rules_snapshot = dict(version.eligibility_rules)

        # 3. Two-step workflow transition with explicit audit trails:
        # Step 3a: DRAFT -> SUBMITTED
        app.submitted_at = datetime.now(timezone.utc)
        app.status = ApplicationStatus.SUBMITTED
        self.db.commit()
        self.db.refresh(app)

        self.audit_repo.log_event(
            entity_type="APPLICATION",
            entity_id=str(app.id),
            application_id=app.id,
            actor_id=applicant_id,
            action="APPLICATION_SUBMITTED",
            previous_status=str(ApplicationStatus.DRAFT.value),
            new_status=str(ApplicationStatus.SUBMITTED.value),
            details={
                "reference_id": app.reference_id,
                "scheme_version_id": str(app.scheme_version_id) if app.scheme_version_id else None,
            },
        )

        # Step 3b: SUBMITTED -> UNDER_AI_VERIFICATION
        app.status = ApplicationStatus.UNDER_AI_VERIFICATION
        self.db.commit()
        self.db.refresh(app)

        self.audit_repo.log_event(
            entity_type="APPLICATION",
            entity_id=str(app.id),
            application_id=app.id,
            actor_id=applicant_id,
            action="APPLICATION_QUEUED_FOR_AI_VERIFICATION",
            previous_status=str(ApplicationStatus.SUBMITTED.value),
            new_status=str(ApplicationStatus.UNDER_AI_VERIFICATION.value),
            details={
                "reference_id": app.reference_id,
                "note": "Queued for Phase 3 document verification",
            },
        )

        # Step 3c: Execute document verification pipeline if requested
        if trigger_verification:
            from app.services.verification_service import DocumentVerificationService
            verif_service = DocumentVerificationService(self.db)
            verif_service.verify_application_documents(app.id, actor_id=applicant_id)
            self.db.refresh(app)

        return ApplicationResponse.model_validate(app)


    def get_application(self, application_id: uuid.UUID) -> ApplicationResponse:
        app = self.repo.get_by_id(application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")
        return ApplicationResponse.model_validate(app)

    def list_by_applicant(self, applicant_id: uuid.UUID) -> List[ApplicationResponse]:
        apps = self.repo.get_by_applicant(applicant_id)
        return [ApplicationResponse.model_validate(a) for a in apps]

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ApplicationResponse]:
        apps = self.repo.get_all(skip=skip, limit=limit)
        return [ApplicationResponse.model_validate(a) for a in apps]

    def update_application(
        self,
        application_id: uuid.UUID,
        data: ApplicationUpdate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> ApplicationResponse:
        app = self.repo.get_by_id(application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        prev_status = app.status
        if data.status and data.status != app.status:
            if not can_transition_application(app.status, data.status):
                raise InvalidStatusTransitionException(
                    "APPLICATION", str(app.status), str(data.status)
                )
            app.status = data.status

        if data.form_data is not None:
            app.form_data = data.form_data

        updated = self.repo.update(app)

        # Audit log for status update or form update
        if data.status and data.status != prev_status:
            self.audit_repo.log_event(
                entity_type="APPLICATION",
                entity_id=str(updated.id),
                application_id=updated.id,
                actor_id=actor_id,
                action="APPLICATION_STATUS_UPDATED",
                previous_status=str(prev_status.value if hasattr(prev_status, "value") else prev_status),
                new_status=str(data.status.value if hasattr(data.status, "value") else data.status),
                details={"reference_id": updated.reference_id},
            )
        elif data.form_data is not None:
            self.audit_repo.log_event(
                entity_type="APPLICATION",
                entity_id=str(updated.id),
                application_id=updated.id,
                actor_id=actor_id,
                action="APPLICATION_UPDATED",
                details={"reference_id": updated.reference_id},
            )

        return ApplicationResponse.model_validate(updated)

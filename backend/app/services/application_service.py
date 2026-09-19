import uuid
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.enums import ApplicationStatus
from app.core.status_transitions import can_transition_application
from app.core.exceptions import (
    EntityNotFoundException,
    InvalidStatusTransitionException,
)
from app.models.application import Application
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
    submission, status transitions, and audit trail generation.
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

    def submit_application(
        self, application_id: uuid.UUID, applicant_id: uuid.UUID
    ) -> ApplicationResponse:
        app = self.repo.get_by_id(application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        if app.applicant_id != applicant_id:
            raise EntityNotFoundException("Application not found for current user")

        if not can_transition_application(app.status, ApplicationStatus.SUBMITTED):
            raise InvalidStatusTransitionException(
                "APPLICATION", str(app.status), str(ApplicationStatus.SUBMITTED)
            )

        # Ensure scheme_version_id is bound and freeze rules snapshot
        if not app.scheme_version_id:
            active_version = self.scheme_version_repo.get_active_version(app.scheme_id)
            if active_version:
                app.scheme_version_id = active_version.id
                app.frozen_rules_snapshot = dict(active_version.eligibility_rules)
        else:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
            if version:
                app.frozen_rules_snapshot = dict(version.eligibility_rules)

        prev_status = app.status
        app.status = ApplicationStatus.SUBMITTED
        app.submitted_at = datetime.now(timezone.utc)
        updated = self.repo.update(app)

        self.audit_repo.log_event(
            entity_type="APPLICATION",
            entity_id=str(updated.id),
            application_id=updated.id,
            actor_id=applicant_id,
            action="APPLICATION_SUBMITTED",
            previous_status=str(prev_status.value if hasattr(prev_status, "value") else prev_status),
            new_status=str(ApplicationStatus.SUBMITTED.value),
            details={
                "reference_id": updated.reference_id,
                "scheme_version_id": str(updated.scheme_version_id) if updated.scheme_version_id else None,
            },
        )
        return ApplicationResponse.model_validate(updated)

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
        return ApplicationResponse.model_validate(updated)

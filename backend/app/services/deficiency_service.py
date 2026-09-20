import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, List, Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, DocumentStatus, AuditEntityType, NotificationChannel
from app.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
)
from app.models.application import Application
from app.models.document import Document
from app.models.deficiency import Deficiency
from app.models.user import User
from app.schemas.deficiency import (
    PublicDeficiencyItem,
    PublicDeficiencyListResponse,
    DeficiencyReplacementUploadResponse,
    ApplicationResubmitRequest,
    ApplicationResubmitResponse,
)
from app.services.storage_service import BaseStorageService, LocalStorageService
from app.services.file_validator import validate_file
from app.services.notification_service import NotificationService
from app.services.verification_service import DocumentVerificationService
from app.repositories.audit_repo import AuditRepository
from app.repositories.scheme_version_repo import SchemeVersionRepository

logger = logging.getLogger(__name__)


def _run_background_verification(application_id: uuid.UUID, actor_id: uuid.UUID):
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        verif_service = DocumentVerificationService(db)
        verif_service.verify_application_documents(application_id, actor_id=actor_id)
    except Exception as e:
        logger.error(f"Background verification error for application {application_id}: {e}")
    finally:
        db.close()


class DeficiencyService:
    """
    Service managing Phase 5 deficiency resolution and applicant resubmission workflows.
    Enforces atomic row-locking, UUID storage, document lineage, applicant privacy,
    and seamless Phase 3 verification pipeline handoff.
    """

    def __init__(
        self,
        db: Session,
        storage_service: Optional[BaseStorageService] = None,
    ):
        self.db = db
        self.storage = storage_service or LocalStorageService()
        self.audit_repo = AuditRepository(db)
        self.scheme_version_repo = SchemeVersionRepository(db)
        self.notification_service = NotificationService(db)

    def get_applicant_deficiencies(
        self, application_id: uuid.UUID, user: User
    ) -> PublicDeficiencyListResponse:
        """
        Retrieves sanitized deficiency items for the application owner.
        Hides internal AI confidence, raw OCR metadata, and internal officer remarks.
        """
        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        # Object-level authorization: Only owner (or officer/admin) can view
        if user.role == "APPLICANT" and app.applicant_id != user.id:
            raise ForbiddenException("Cannot access deficiencies for an application belonging to another user")

        deficiencies = (
            self.db.query(Deficiency)
            .filter(Deficiency.application_id == application_id)
            .order_by(Deficiency.cycle.asc(), Deficiency.created_at.asc())
            .all()
        )

        # Load scheme version for human-friendly document labels
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        label_map = {}
        if version and version.required_documents:
            for doc_cfg in version.required_documents.get("documents", []):
                code = doc_cfg.get("code") or doc_cfg.get("type")
                label = doc_cfg.get("label") or doc_cfg.get("name") or code
                label_map[code] = label

        items: List[PublicDeficiencyItem] = []
        for d in deficiencies:
            doc_type = d.document.document_type if d.document else "UNKNOWN_DOCUMENT"
            doc_label = label_map.get(doc_type, doc_type.replace("_", " ").title())

            items.append(
                PublicDeficiencyItem(
                    id=d.id,
                    application_id=d.application_id,
                    cycle=d.cycle,
                    document_id=d.document_id,
                    document_type=doc_type,
                    document_name=doc_label,
                    reason=d.reason,
                    applicant_message=d.applicant_message,
                    applicant_remarks=d.applicant_remarks,
                    status=d.status,
                    created_at=d.created_at,
                    replacement_document_id=d.replacement_document_id,
                    replacement_uploaded_at=d.replacement_uploaded_at,
                    resolved_at=d.resolved_at,
                )
            )

        open_count = sum(1 for d in deficiencies if d.status == "OPEN")
        rep_count = sum(1 for d in deficiencies if d.status == "REPLACEMENT_UPLOADED")
        under_review_count = sum(1 for d in deficiencies if d.status == "UNDER_REVIEW")
        resolved_count = sum(1 for d in deficiencies if d.status == "RESOLVED")

        # Applicant can resubmit only when application is DEFICIENT, there are active deficiencies,
        # and none remain in OPEN status
        can_resubmit = (
            app.status == ApplicationStatus.DEFICIENT
            and len(deficiencies) > 0
            and open_count == 0
            and rep_count > 0
        )

        return PublicDeficiencyListResponse(
            application_id=app.id,
            application_status=str(app.status.value if hasattr(app.status, "value") else app.status),
            total=len(deficiencies),
            open_count=open_count,
            replacement_uploaded_count=rep_count,
            under_review_count=under_review_count,
            resolved_count=resolved_count,
            can_resubmit=can_resubmit,
            items=items,
        )

    def upload_replacement_document(
        self,
        application_id: uuid.UUID,
        deficiency_id: uuid.UUID,
        filename: str,
        file_obj: BinaryIO,
        applicant_remarks: Optional[str],
        user: User,
    ) -> DeficiencyReplacementUploadResponse:
        """
        Uploads a replacement document for a specific itemized deficiency.
        Atomic concurrency rules:
          1. Row lock on Application and Deficiency.
          2. Exactly one document per document_type remains is_current = True.
          3. If replacement was already uploaded in this cycle, it is superseded (monotonic version lineage).
          4. Physical storage uses pure UUIDs; version and original filename stored as metadata.
          5. Sets deficiency.status = 'REPLACEMENT_UPLOADED' (NOT 'RESOLVED').
        """
        # Row-level lock on Application and Deficiency
        app = (
            self.db.query(Application)
            .filter(Application.id == application_id)
            .with_for_update()
            .first()
        )
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        if user.role == "APPLICANT" and app.applicant_id != user.id:
            raise ForbiddenException("Cannot upload replacement for an application belonging to another user")

        if app.status != ApplicationStatus.DEFICIENT:
            raise ConflictException(
                f"Application is in status '{app.status.value if hasattr(app.status, 'value') else app.status}', "
                "not 'DEFICIENT'. Replacements can only be uploaded while the application is in DEFICIENT status."
            )

        deficiency = (
            self.db.query(Deficiency)
            .filter(Deficiency.id == deficiency_id, Deficiency.application_id == application_id)
            .with_for_update()
            .first()
        )
        if not deficiency:
            raise EntityNotFoundException(f"Deficiency with ID {deficiency_id} not found on this application")

        if deficiency.status not in ("OPEN", "REPLACEMENT_UPLOADED"):
            raise ConflictException(
                f"Deficiency is in status '{deficiency.status}', and cannot accept replacement uploads."
            )

        # Retrieve target document type and constraints
        original_doc = self.db.get(Document, deficiency.document_id)
        if not original_doc:
            raise EntityNotFoundException("Original deficient document not found")

        doc_type = original_doc.document_type

        # Load scheme version document constraints
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        allowed_extensions = None
        max_size_bytes = 5 * 1024 * 1024
        if version and version.required_documents:
            for doc_cfg in version.required_documents.get("documents", []):
                code = doc_cfg.get("code") or doc_cfg.get("type")
                if code == doc_type:
                    if doc_cfg.get("allowed_extensions"):
                        allowed_extensions = doc_cfg.get("allowed_extensions")
                    if doc_cfg.get("max_size_bytes"):
                        max_size_bytes = doc_cfg.get("max_size_bytes")
                    elif doc_cfg.get("max_size_mb"):
                        max_size_bytes = doc_cfg.get("max_size_mb") * 1024 * 1024
                    break

        # Validate file safety (magic bytes, MIME type, size, extension)
        clean_filename, verified_mime, file_size = validate_file(
            file_obj=file_obj,
            filename=filename,
            allowed_extensions=allowed_extensions,
            max_size_bytes=max_size_bytes,
        )

        # Generate UUID for new replacement document
        new_doc_id = uuid.uuid4()
        ext = Path(clean_filename).suffix.lower()
        storage_filename = f"{new_doc_id.hex}{ext}"
        subfolder = f"applications/{application_id}/documents"

        # Save physical file using UUID path (security requirement)
        storage_path = self.storage.save_file(
            file_obj=file_obj, filename=storage_filename, subfolder=subfolder
        )

        now_utc = datetime.now(timezone.utc)

        # Determine version and parent lineage
        prior_doc_to_supersede = None
        if deficiency.replacement_document_id:
            prior_rep = self.db.get(Document, deficiency.replacement_document_id)
            if prior_rep:
                prior_doc_to_supersede = prior_rep
                new_version = prior_rep.version + 1
                parent_id = prior_rep.id
            else:
                prior_doc_to_supersede = original_doc
                new_version = original_doc.version + 1
                parent_id = original_doc.id
        else:
            prior_doc_to_supersede = original_doc
            new_version = original_doc.version + 1
            parent_id = original_doc.id

        # Guarantee invariant: Ensure all existing documents for this application + document_type are is_current = False
        self.db.query(Document).filter(
            Document.application_id == application_id,
            Document.document_type == doc_type,
        ).update({"is_current": False})

        # Insert new Document record first
        new_doc = Document(
            id=new_doc_id,
            application_id=app.id,
            document_type=doc_type,
            original_filename=clean_filename,
            storage_path=storage_path,
            mime_type=verified_mime,
            file_size=file_size,
            status=DocumentStatus.PENDING,
            version=new_version,
            is_current=True,
            parent_document_id=parent_id,
        )
        self.db.add(new_doc)
        # Flush so new_doc exists in database before setting foreign key superseded_by_id
        self.db.flush()

        # Now link predecessor to this newly inserted document
        if prior_doc_to_supersede:
            prior_doc_to_supersede.superseded_by_id = new_doc_id
            prior_doc_to_supersede.is_current = False

        # Update Deficiency record (Status = REPLACEMENT_UPLOADED, strictly NOT RESOLVED)
        prev_def_status = deficiency.status
        deficiency.replacement_document_id = new_doc_id
        deficiency.applicant_remarks = applicant_remarks.strip() if applicant_remarks else None
        deficiency.replacement_uploaded_at = now_utc
        deficiency.status = "REPLACEMENT_UPLOADED"

        self.db.commit()
        self.db.refresh(new_doc)
        self.db.refresh(deficiency)

        # Audit log event
        self.audit_repo.log_event(
            entity_type=AuditEntityType.DOCUMENT,
            entity_id=str(new_doc.id),
            application_id=app.id,
            actor_id=user.id,
            action="DEFICIENCY_REPLACEMENT_UPLOADED",
            previous_status=prev_def_status,
            new_status="REPLACEMENT_UPLOADED",
            details={
                "deficiency_id": str(deficiency.id),
                "document_type": doc_type,
                "version": new_version,
                "parent_document_id": str(parent_id),
                "original_filename": clean_filename,
                "applicant_remarks": deficiency.applicant_remarks,
            },
        )

        return DeficiencyReplacementUploadResponse(
            deficiency_id=deficiency.id,
            status=deficiency.status,
            document_id=new_doc.id,
            version=new_doc.version,
            original_filename=new_doc.original_filename,
            applicant_remarks=deficiency.applicant_remarks,
            uploaded_at=now_utc,
            message="Replacement document uploaded successfully. You can resubmit once all deficiencies are resolved.",
        )

    def resubmit_application(
        self,
        application_id: uuid.UUID,
        data: ApplicationResubmitRequest,
        user: User,
        background_tasks: Optional[BackgroundTasks] = None,
        sync_verify: bool = False,
    ) -> ApplicationResubmitResponse:
        """
        Finalizes application resubmission.
        Strict Invariants:
          1. Application must be in DEFICIENT status (atomic row-lock).
          2. All active deficiencies must be in REPLACEMENT_UPLOADED status.
          3. Two explicit auditable transitions:
             DEFICIENT -> RESUBMITTED (audit: APPLICATION_RESUBMITTED)
             RESUBMITTED -> UNDER_AI_VERIFICATION (audit: APPLICATION_QUEUED_FOR_AI_VERIFICATION)
          4. Deficiencies transition to UNDER_REVIEW.
          5. Reuses Phase 3 DocumentVerificationService for active documents.
        """
        app = (
            self.db.query(Application)
            .filter(Application.id == application_id)
            .with_for_update()
            .first()
        )
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        if user.role == "APPLICANT" and app.applicant_id != user.id:
            raise ForbiddenException("Cannot resubmit application belonging to another user")

        if app.status != ApplicationStatus.DEFICIENT:
            raise ConflictException(
                f"Application is in status '{app.status.value if hasattr(app.status, 'value') else app.status}', "
                "not 'DEFICIENT'. Resubmission is only allowed for DEFICIENT applications."
            )

        if not data.declaration_confirmed:
            raise ValidationException("Applicant declaration must be confirmed before resubmission")

        # Check deficiency prerequisites
        deficiencies = (
            self.db.query(Deficiency)
            .filter(Deficiency.application_id == application_id)
            .all()
        )

        open_defs = [d for d in deficiencies if d.status == "OPEN"]
        if open_defs:
            raise ValidationException(
                f"Cannot resubmit application: {len(open_defs)} deficiency item(s) remain OPEN without uploaded replacements. "
                "All deficiencies must have replacement documents uploaded before resubmission."
            )

        rep_defs = [d for d in deficiencies if d.status == "REPLACEMENT_UPLOADED"]
        if not rep_defs:
            raise ValidationException("No replacements have been uploaded for resubmission.")

        now_utc = datetime.now(timezone.utc)
        prev_status = app.status

        # ---------------------------------------------------------------------
        # Transition 1: DEFICIENT -> RESUBMITTED
        # ---------------------------------------------------------------------
        app.status = ApplicationStatus.RESUBMITTED
        app.resubmission_count += 1
        app.resubmitted_at = now_utc

        # Update active deficiencies to UNDER_REVIEW
        for d in rep_defs:
            d.status = "UNDER_REVIEW"

        self.db.commit()
        self.db.refresh(app)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.APPLICATION,
            entity_id=str(app.id),
            application_id=app.id,
            actor_id=user.id,
            action="APPLICATION_RESUBMITTED",
            previous_status=str(prev_status.value),
            new_status=str(ApplicationStatus.RESUBMITTED.value),
            details={
                "resubmission_count": app.resubmission_count,
                "deficiencies_cured": len(rep_defs),
                "remarks": data.remarks,
            },
        )

        # ---------------------------------------------------------------------
        # Transition 2: RESUBMITTED -> UNDER_AI_VERIFICATION
        # ---------------------------------------------------------------------
        app.status = ApplicationStatus.UNDER_AI_VERIFICATION
        self.db.commit()
        self.db.refresh(app)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.APPLICATION,
            entity_id=str(app.id),
            application_id=app.id,
            actor_id=user.id,
            action="APPLICATION_QUEUED_FOR_AI_VERIFICATION",
            previous_status=str(ApplicationStatus.RESUBMITTED.value),
            new_status=str(ApplicationStatus.UNDER_AI_VERIFICATION.value),
            details={
                "target": "DocumentVerificationService",
                "resubmission_count": app.resubmission_count,
            },
        )

        # Trigger Phase 3 AI Verification pipeline
        if sync_verify:
            verif_service = DocumentVerificationService(self.db)
            verif_service.verify_application_documents(app.id, actor_id=user.id)
            self.db.refresh(app)
        elif background_tasks:
            background_tasks.add_task(_run_background_verification, app.id, user.id)

        return ApplicationResubmitResponse(
            application_id=app.id,
            reference_id=app.reference_id,
            status=str(app.status.value if hasattr(app.status, "value") else app.status),
            resubmission_count=app.resubmission_count,
            resubmitted_at=now_utc,
            message="Application resubmitted successfully and queued for AI verification.",
        )

    def dispatch_pending_deficiency_notifications(
        self, application_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Phase 5 Notification Dispatcher:
        Scans for unnotified OPEN deficiencies and sends in-app notifications to applicants.
        Phase 4 code remains completely free of notification dispatch calls.
        """
        query = self.db.query(Deficiency).filter(
            Deficiency.status == "OPEN",
            Deficiency.notification_dispatched == False,  # noqa: E712
        )
        if application_id:
            query = query.filter(Deficiency.application_id == application_id)

        unnotified_defs = query.all()
        if not unnotified_defs:
            return 0

        # Group by application
        app_groups = {}
        for d in unnotified_defs:
            app_groups.setdefault(d.application_id, []).append(d)

        now_utc = datetime.now(timezone.utc)
        dispatched_count = 0

        for app_id, def_list in app_groups.items():
            app = self.db.get(Application, app_id)
            if not app:
                continue

            title = f"Action Required: Deficiencies flagged on application {app.reference_id}"
            items_summary = "\n".join(
                f"- {d.document.document_type if d.document else 'Document'}: {d.applicant_message}"
                for d in def_list
            )
            message = (
                f"Your application {app.reference_id} has {len(def_list)} item(s) requiring replacement:\n"
                f"{items_summary}\n\nPlease review and upload replacements."
            )

            self.notification_service.send_notification(
                user_id=app.applicant_id,
                title=title,
                message=message,
                channel=NotificationChannel.IN_APP,
                application_id=app.id,
            )

            for d in def_list:
                d.notification_dispatched = True
                d.notification_dispatched_at = now_utc
            dispatched_count += len(def_list)

        self.db.commit()
        return dispatched_count

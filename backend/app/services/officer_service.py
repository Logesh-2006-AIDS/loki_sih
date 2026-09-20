import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from app.core.enums import UserRole, ApplicationStatus, DocumentStatus, AuditEntityType
from app.core.status_transitions import can_transition_document, can_transition_application
from app.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
    ConflictException,
    InvalidStatusTransitionException,
)
from app.api.deps import check_officer_application_scope
from app.models.user import User
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.officer_assignment import OfficerAssignment
from app.models.deficiency import Deficiency
from app.repositories.audit_repo import AuditRepository
from app.repositories.scheme_version_repo import SchemeVersionRepository
from app.schemas.officer import (
    OfficerQueueItem,
    OfficerQueueResponse,
    OfficerQueueCounts,
    OfficerDocumentScrutinyItem,
    OfficerApplicationScrutinyResponse,
    OfficerDocumentDecisionRequest,
    OfficerApplicationDecisionRequest,
    OfficerStatsResponse,
)

logger = logging.getLogger(__name__)


class OfficerService:
    """
    Domain service orchestrating human officer verification workflows:
    - Jurisdiction-restricted application queue with PII minimization
    - Deep application and document scrutiny payload retrieval
    - Individual document decision processing with explicit AI override logic
    - Application-level scrutiny finalization with strict human-verification invariants
    - Seamless Phase 5 deficiency contract handoff (zero premature notifications)
    - Full entity-level audit logging and concurrency control
    """

    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditRepository(db)
        self.scheme_version_repo = SchemeVersionRepository(db)

    def _get_officer_scope(self, officer: User) -> Dict[str, Any]:
        """
        Determines the scope of applications an officer is allowed to see.
        Returns:
          {"is_global": bool, "scheme_ids": List[UUID], "states": List[str], "has_access": bool}
        """
        user_role = officer.role
        if isinstance(user_role, str):
            user_role = UserRole(user_role)

        if user_role == UserRole.ADMIN:
            return {"is_global": True, "scheme_ids": [], "states": [], "has_access": True}

        assignments = (
            self.db.query(OfficerAssignment)
            .filter(
                OfficerAssignment.officer_id == officer.id,
                OfficerAssignment.is_active == True,
            )
            .all()
        )

        if not assignments:
            return {"is_global": False, "scheme_ids": [], "states": [], "has_access": False}

        # Check for explicit global assignment (scheme_id is None AND state is None)
        for assign in assignments:
            if assign.scheme_id is None and assign.state is None:
                return {"is_global": True, "scheme_ids": [], "states": [], "has_access": True}

        scheme_ids = [a.scheme_id for a in assignments if a.scheme_id is not None]
        states = [a.state for a in assignments if a.state is not None]

        return {
            "is_global": False,
            "scheme_ids": scheme_ids,
            "states": states,
            "assignments": assignments,
            "has_access": True,
        }

    def get_queue(
        self,
        officer: User,
        status_filter: Optional[str] = None,
        scheme_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        search: Optional[str] = None,
        has_ai_flags: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> OfficerQueueResponse:
        """
        Fetches the paginated queue of applications available to the officer.
        Enforces server-side jurisdiction and excludes applicant contact PII.
        """
        scope = self._get_officer_scope(officer)
        if not scope["has_access"]:
            # Officer has no active assignments; return empty queue
            return OfficerQueueResponse(
                total=0,
                skip=skip,
                limit=limit,
                counts=OfficerQueueCounts(),
                items=[],
            )

        # Base query joined with User and Scheme
        query = (
            self.db.query(Application)
            .join(User, Application.applicant_id == User.id)
            .join(Scheme, Application.scheme_id == Scheme.id)
        )

        # Apply jurisdiction filtering if not global
        if not scope["is_global"]:
            assignments = scope["assignments"]
            or_conditions = []
            for a in assignments:
                conds = []
                if a.scheme_id is not None:
                    conds.append(Application.scheme_id == a.scheme_id)
                if a.state is not None:
                    # Match state in form_data.personal.state or form_data.state
                    conds.append(
                        or_(
                            Application.form_data["personal"]["state"].astext == a.state,
                            Application.form_data["state"].astext == a.state,
                        )
                    )
                if conds:
                    or_conditions.append(and_(*conds))
            if or_conditions:
                query = query.filter(or_(*or_conditions))
            else:
                return OfficerQueueResponse(
                    total=0,
                    skip=skip,
                    limit=limit,
                    counts=OfficerQueueCounts(),
                    items=[],
                )

        # Exclude draft applications; officers only scrutinize submitted applications
        query = query.filter(Application.status != ApplicationStatus.DRAFT)

        # Calculate counts across statuses for KPI indicators within officer's scope
        all_apps = query.all()
        pending_count = sum(1 for a in all_apps if a.status == ApplicationStatus.UNDER_MANUAL_REVIEW)
        verified_count = sum(1 for a in all_apps if a.status == ApplicationStatus.VERIFIED)
        deficient_count = sum(1 for a in all_apps if a.status == ApplicationStatus.DEFICIENT)
        rejected_count = sum(1 for a in all_apps if a.status == ApplicationStatus.REJECTED)
        total_in_scope = len(all_apps)

        counts = OfficerQueueCounts(
            pending_review=pending_count,
            verified=verified_count,
            deficient=deficient_count,
            rejected=rejected_count,
            all=total_in_scope,
        )

        # Apply Status Filter
        if status_filter and status_filter.upper() != "ALL":
            try:
                target_status = ApplicationStatus(status_filter.upper())
                query = query.filter(Application.status == target_status)
            except ValueError:
                pass
        elif not status_filter:
            # Default view: applications currently awaiting desk scrutiny
            query = query.filter(Application.status == ApplicationStatus.UNDER_MANUAL_REVIEW)

        # Apply Scheme Filter
        if scheme_id:
            query = query.filter(Application.scheme_id == scheme_id)

        # Apply State Filter
        if state:
            query = query.filter(
                or_(
                    Application.form_data["personal"]["state"].astext == state,
                    Application.form_data["state"].astext == state,
                )
            )

        # Apply Text Search (Reference ID or Applicant Full Name)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Application.reference_id.ilike(term),
                    User.full_name.ilike(term),
                )
            )

        # Filter by AI Flag presence if requested
        if has_ai_flags is not None:
            # Subquery to check for flagged documents
            flagged_doc_subq = (
                self.db.query(Document.application_id)
                .filter(Document.status == DocumentStatus.FLAGGED)
                .subquery()
            )
            if has_ai_flags:
                query = query.filter(Application.id.in_(select(flagged_doc_subq)))
            else:
                query = query.filter(Application.id.not_in(select(flagged_doc_subq)))

        # Ordering & Pagination: Oldest pending submissions first (FIFO)
        total_filtered = query.count()
        applications = (
            query.order_by(Application.submitted_at.asc().nulls_last(), Application.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        items: List[OfficerQueueItem] = []
        for app in applications:
            applicant = app.applicant
            scheme = app.scheme
            docs = app.documents or []

            # Determine AI flags & confidence summary from document verifications
            flagged_count = sum(1 for d in docs if d.status == DocumentStatus.FLAGGED)
            ai_status = "VERIFIED" if docs and all(d.status == DocumentStatus.VERIFIED for d in docs) else "FLAGGED" if flagged_count > 0 else "PROCESSING"
            
            # Extract state from form_data
            app_state = (
                (app.form_data or {}).get("personal", {}).get("state")
                or (app.form_data or {}).get("state")
            )

            # Compute average confidence across document verifications if present
            confidences = []
            for d in docs:
                for v in d.verifications or []:
                    if v.overall_confidence is not None:
                        confidences.append(v.overall_confidence)
            avg_conf = sum(confidences) / len(confidences) if confidences else None

            items.append(
                OfficerQueueItem(
                    id=app.id,
                    reference_id=app.reference_id,
                    scheme_id=scheme.id,
                    scheme_code=scheme.scheme_code,
                    scheme_name=scheme.name,
                    applicant_name=applicant.full_name if applicant else "Unknown Applicant",
                    state=app_state,
                    status=str(app.status.value if hasattr(app.status, "value") else app.status),
                    submitted_at=app.submitted_at,
                    total_documents=len(docs),
                    ai_flagged_count=flagged_count,
                    ai_status=ai_status,
                    overall_confidence=avg_conf,
                )
            )

        return OfficerQueueResponse(
            total=total_filtered,
            skip=skip,
            limit=limit,
            counts=counts,
            items=items,
        )

    def get_scrutiny_details(
        self, officer: User, application_id: uuid.UUID
    ) -> OfficerApplicationScrutinyResponse:
        """
        Loads the complete scrutiny package for an application.
        Strictly enforces officer jurisdiction server-side.
        """
        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException("APPLICATION", application_id)

        # Enforce server-side jurisdiction check
        if not check_officer_application_scope(self.db, officer.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

        applicant = app.applicant
        scheme = app.scheme
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        # Fetch documents and map to scrutiny items
        documents = app.documents or []
        doc_items: List[OfficerDocumentScrutinyItem] = []

        for doc in documents:
            # Latest authoritative DocumentVerification record
            verification = (
                self.db.query(DocumentVerification)
                .filter(DocumentVerification.document_id == doc.id)
                .order_by(DocumentVerification.created_at.desc())
                .first()
            )

            verifier_name = None
            if verification and verification.verified_by:
                verifier_user = self.db.get(User, verification.verified_by)
                if verifier_user:
                    verifier_name = verifier_user.full_name

            doc_items.append(
                OfficerDocumentScrutinyItem(
                    id=doc.id,
                    document_type=doc.document_type,
                    original_filename=doc.original_filename,
                    mime_type=doc.mime_type,
                    file_size=doc.file_size,
                    status=str(doc.status.value if hasattr(doc.status, "value") else doc.status),
                    uploaded_at=doc.uploaded_at,
                    ocr_text=verification.ocr_text if verification else None,
                    extracted_fields=verification.extracted_fields if verification else {},
                    field_confidences=verification.field_confidences if verification else {},
                    comparison_results=verification.comparison_results if verification else {},
                    overall_confidence=verification.overall_confidence if verification else None,
                    flags=verification.flags if verification else [],
                    officer_decision=verification.officer_decision if verification else None,
                    officer_remarks=verification.officer_remarks if verification else None,
                    ai_override=verification.ai_override if verification else False,
                    override_reason=verification.override_reason if verification else None,
                    verified_by=verification.verified_by if verification else None,
                    verified_by_name=verifier_name,
                    verified_at=verification.verified_at if verification else None,
                )
            )

        scrutiny_officer_name = None
        if app.scrutiny_officer_id:
            s_officer = self.db.get(User, app.scrutiny_officer_id)
            if s_officer:
                scrutiny_officer_name = s_officer.full_name

        req_docs_cfg = None
        if version and version.required_documents:
            req_docs_cfg = version.required_documents.get("documents", [])

        return OfficerApplicationScrutinyResponse(
            id=app.id,
            reference_id=app.reference_id,
            status=str(app.status.value if hasattr(app.status, "value") else app.status),
            submitted_at=app.submitted_at,
            applicant_id=applicant.id if applicant else uuid.UUID(int=0),
            applicant_name=applicant.full_name if applicant else "Unknown Applicant",
            applicant_email=applicant.email if applicant else "",
            applicant_phone=applicant.phone if applicant else None,
            scheme_id=scheme.id,
            scheme_code=scheme.scheme_code,
            scheme_name=scheme.name,
            scheme_version=version.scheme_version if version else "1.0",
            eligibility_rules=version.eligibility_rules if version else scheme.eligibility_rules,
            form_schema=version.form_schema if version else scheme.form_schema,
            required_documents_config=req_docs_cfg,
            form_data=app.form_data or {},
            documents=doc_items,
            scrutiny_remarks=app.scrutiny_remarks,
            scrutiny_officer_id=app.scrutiny_officer_id,
            scrutiny_officer_name=scrutiny_officer_name,
            scrutiny_completed_at=app.scrutiny_completed_at,
        )

    def record_document_decision(
        self,
        officer: User,
        document_id: uuid.UUID,
        data: OfficerDocumentDecisionRequest,
    ) -> OfficerDocumentScrutinyItem:
        """
        Records an authoritative human officer decision on a single document.
        Invariants:
          - Document rejection does NOT modify the parent application status.
          - If AI flagged the document and human marks it VERIFIED, ai_override must be true and override_reason non-empty.
          - Decisions are saved durably with audit logging and verifier metadata.
        """
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException("DOCUMENT", document_id)

        app = self.db.get(Application, doc.application_id)
        if not app:
            raise EntityNotFoundException("APPLICATION", doc.application_id)

        # Enforce server-side jurisdiction
        if not check_officer_application_scope(self.db, officer.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this document")

        decision_upper = data.decision.strip().upper()
        if decision_upper not in ("VERIFIED", "RESUBMISSION_REQUIRED", "REJECTED"):
            raise ValidationException(
                f"Invalid document decision: '{data.decision}'. Must be VERIFIED, RESUBMISSION_REQUIRED, or REJECTED."
            )

        # Find or initialize DocumentVerification record
        verification = (
            self.db.query(DocumentVerification)
            .filter(DocumentVerification.document_id == document_id)
            .order_by(DocumentVerification.created_at.desc())
            .first()
        )

        now_utc = datetime.now(timezone.utc)
        if not verification:
            verification = DocumentVerification(
                document_id=doc.id,
                verification_status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
                verification_source="MANUAL_OFFICER",
                created_at=now_utc,
            )
            self.db.add(verification)

        # Evaluate AI flag presence
        ai_had_flags = False
        if verification.flags and len(verification.flags) > 0:
            ai_had_flags = True
        if doc.status == DocumentStatus.FLAGGED or verification.verification_status == "FLAGGED":
            ai_had_flags = True

        # AI Override Validation Rule
        is_override = False
        override_reason = None
        if decision_upper == "VERIFIED" and ai_had_flags:
            if not data.ai_override or not data.override_reason or not data.override_reason.strip():
                raise ValidationException(
                    "This document has AI verification flags. Overriding AI flags to mark the document as VERIFIED "
                    "requires setting ai_override to true and providing a non-empty override_reason."
                )
            is_override = True
            override_reason = data.override_reason.strip()
        elif data.ai_override and data.override_reason:
            is_override = True
            override_reason = data.override_reason.strip()

        # Remarks validation for deficiency or rejection
        if decision_upper in ("RESUBMISSION_REQUIRED", "REJECTED"):
            if not data.remarks or not data.remarks.strip():
                raise ValidationException(
                    f"Remarks are mandatory when marking a document as {decision_upper}."
                )

        # Transition DocumentStatus
        prev_doc_status = doc.status
        new_doc_status = (
            DocumentStatus.VERIFIED
            if decision_upper == "VERIFIED"
            else DocumentStatus.RESUBMISSION_REQUIRED
            if decision_upper == "RESUBMISSION_REQUIRED"
            else DocumentStatus.REJECTED
        )

        if not can_transition_document(prev_doc_status, new_doc_status):
            raise InvalidStatusTransitionException("DOCUMENT", str(prev_doc_status), str(new_doc_status))

        doc.status = new_doc_status

        # Update verification record with human decision
        verification.officer_decision = decision_upper
        verification.officer_remarks = data.remarks.strip() if data.remarks else None
        verification.ai_override = is_override
        verification.override_reason = override_reason
        verification.verified_by = officer.id
        verification.verified_at = now_utc

        self.db.commit()
        self.db.refresh(doc)
        self.db.refresh(verification)

        # Audit document decision
        self.audit_repo.log_event(
            entity_type="DOCUMENT",
            entity_id=str(doc.id),
            application_id=app.id,
            actor_id=officer.id,
            action="OFFICER_DOCUMENT_DECISION",
            previous_status=str(prev_doc_status.value if hasattr(prev_doc_status, "value") else prev_doc_status),
            new_status=str(new_doc_status.value),
            details={
                "document_type": doc.document_type,
                "officer_decision": decision_upper,
                "remarks": data.remarks,
                "ai_override": is_override,
                "override_reason": override_reason,
            },
        )

        # If human officer overrode AI flags, log a high-visibility audit event
        if is_override:
            self.audit_repo.log_event(
                entity_type="DOCUMENT",
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=officer.id,
                action="OFFICER_AI_FLAG_OVERRIDDEN",
                details={
                    "document_type": doc.document_type,
                    "previous_status": str(prev_doc_status.value if hasattr(prev_doc_status, "value") else prev_doc_status),
                    "human_decision": decision_upper,
                    "override_reason": override_reason,
                    "flag_count": len(verification.flags or []),
                },
            )

        return OfficerDocumentScrutinyItem(
            id=doc.id,
            document_type=doc.document_type,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            status=str(doc.status.value),
            uploaded_at=doc.uploaded_at,
            ocr_text=verification.ocr_text,
            extracted_fields=verification.extracted_fields or {},
            field_confidences=verification.field_confidences or {},
            comparison_results=verification.comparison_results or {},
            overall_confidence=verification.overall_confidence,
            flags=verification.flags or [],
            officer_decision=verification.officer_decision,
            officer_remarks=verification.officer_remarks,
            ai_override=verification.ai_override,
            override_reason=verification.override_reason,
            verified_by=verification.verified_by,
            verified_by_name=officer.full_name,
            verified_at=verification.verified_at,
        )

    def record_application_decision(
        self,
        officer: User,
        application_id: uuid.UUID,
        data: OfficerApplicationDecisionRequest,
    ) -> Application:
        """
        Submits the authoritative human scrutiny determination for the entire application.
        Strict Invariants Enforced:
          1. Concurrency: atomic guard ensures application is currently in UNDER_MANUAL_REVIEW.
          2. Approval Guard: Application VERIFIED requires every mandatory document to have an explicit
             human officer_decision == 'VERIFIED'. AI DocumentStatus.VERIFIED alone is strictly insufficient.
          3. Rejection Independence: Document rejection does NOT automatically reject application;
             application rejection must be an explicit human decision.
          4. Phase 5 Boundary: If DEFICIENT, creates OPEN deficiency records and halts without sending
             applicant notifications or running resubmission flows.
        """
        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException("APPLICATION", application_id)

        # Enforce server-side jurisdiction
        if not check_officer_application_scope(self.db, officer.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

        # Concurrency check: Application must currently be in UNDER_MANUAL_REVIEW
        if app.status != ApplicationStatus.UNDER_MANUAL_REVIEW:
            raise ConflictException(
                f"Application is in status '{app.status.value if hasattr(app.status, 'value') else app.status}', "
                "not 'UNDER_MANUAL_REVIEW'. It may have already been finalized by another officer."
            )

        decision_upper = data.decision.strip().upper()
        if decision_upper not in ("VERIFIED", "DEFICIENT", "REJECTED"):
            raise ValidationException(
                f"Invalid application decision: '{data.decision}'. Must be VERIFIED, DEFICIENT, or REJECTED."
            )

        now_utc = datetime.now(timezone.utc)
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        documents = app.documents or []
        doc_map = {d.document_type: d for d in documents}

        # ---------------------------------------------------------------------
        # Case 1: Application Approval (VERIFIED)
        # ---------------------------------------------------------------------
        if decision_upper == "VERIFIED":
            # 1. Check for any rejected or deficient documents first
            has_blocked_docs = any(
                d.status in (DocumentStatus.RESUBMISSION_REQUIRED, DocumentStatus.REJECTED)
                for d in documents
            )
            if has_blocked_docs:
                raise ValidationException(
                    "Cannot approve application: One or more documents are marked RESUBMISSION_REQUIRED or REJECTED."
                )

            # 2. Invariant: Every mandatory document must have explicit human officer_decision == "VERIFIED"
            if version and version.required_documents:
                req_doc_configs = [
                    d for d in version.required_documents.get("documents", [])
                    if d.get("required", True)
                ]
                missing_verifications = []
                for req in req_doc_configs:
                    doc_code = req.get("code") or req.get("type")
                    doc_label = req.get("label") or req.get("name") or doc_code
                    doc_obj = doc_map.get(doc_code)

                    if not doc_obj:
                        missing_verifications.append(f"Missing mandatory document: {doc_label}")
                        continue

                    # Retrieve latest verification record
                    verif = (
                        self.db.query(DocumentVerification)
                        .filter(DocumentVerification.document_id == doc_obj.id)
                        .order_by(DocumentVerification.created_at.desc())
                        .first()
                    )

                    # CRITICAL: Require explicit human officer_decision == "VERIFIED"
                    if not verif or verif.officer_decision != "VERIFIED":
                        missing_verifications.append(
                            f"Document '{doc_label}' requires explicit human verification by an officer"
                        )

                if missing_verifications:
                    raise ValidationException(
                        f"Cannot approve application. The following document requirements are unsatisfied: "
                        f"{'; '.join(missing_verifications)}"
                    )

            target_app_status = ApplicationStatus.VERIFIED

        # ---------------------------------------------------------------------
        # Case 2: Application Flagged Deficient (DEFICIENT) -> Phase 5 Handoff
        # ---------------------------------------------------------------------
        elif decision_upper == "DEFICIENT":
            # Must have at least one deficient document or itemized deficiency
            deficient_docs = [d for d in documents if d.status == DocumentStatus.RESUBMISSION_REQUIRED]
            if not deficient_docs and not (data.deficiencies and len(data.deficiencies) > 0):
                raise ValidationException(
                    "Cannot mark application DEFICIENT without at least one document marked RESUBMISSION_REQUIRED "
                    "or an explicit deficiency item listed."
                )

            # Persist initial OPEN deficiency records (Phase 5 handoff contract)
            created_deficiencies = []
            if data.deficiencies:
                for def_in in data.deficiencies:
                    new_def = Deficiency(
                        application_id=app.id,
                        document_id=def_in.document_id,
                        reason=def_in.reason,
                        applicant_message=def_in.applicant_message,
                        status="OPEN",
                        created_at=now_utc,
                    )
                    self.db.add(new_def)
                    created_deficiencies.append(new_def)

            # Auto-create deficiency record for any document marked RESUBMISSION_REQUIRED not in list
            covered_doc_ids = {d.document_id for d in (data.deficiencies or []) if d.document_id}
            for d in deficient_docs:
                if d.id not in covered_doc_ids:
                    # Get remarks from verification
                    v = (
                        self.db.query(DocumentVerification)
                        .filter(DocumentVerification.document_id == d.id)
                        .order_by(DocumentVerification.created_at.desc())
                        .first()
                    )
                    msg = v.officer_remarks if (v and v.officer_remarks) else "Document rejected during desk scrutiny. Resubmission required."
                    new_def = Deficiency(
                        application_id=app.id,
                        document_id=d.id,
                        reason=f"DEFICIENT_{d.document_type}",
                        applicant_message=msg,
                        status="OPEN",
                        created_at=now_utc,
                    )
                    self.db.add(new_def)
                    created_deficiencies.append(new_def)

            target_app_status = ApplicationStatus.DEFICIENT

        # ---------------------------------------------------------------------
        # Case 3: Application Rejected (REJECTED)
        # ---------------------------------------------------------------------
        else:
            if not data.remarks or len(data.remarks.strip()) < 5:
                raise ValidationException(
                    "Rejection requires detailed scrutiny remarks explaining the disqualification grounds."
                )
            target_app_status = ApplicationStatus.REJECTED

        # Transition Application Status
        prev_app_status = app.status
        if not can_transition_application(prev_app_status, target_app_status):
            raise InvalidStatusTransitionException("APPLICATION", str(prev_app_status), str(target_app_status))

        app.status = target_app_status
        app.scrutiny_remarks = data.remarks.strip()
        app.scrutiny_officer_id = officer.id
        app.scrutiny_completed_at = now_utc

        self.db.commit()
        self.db.refresh(app)

        # Audit application scrutiny decision
        self.audit_repo.log_event(
            entity_type="APPLICATION",
            entity_id=str(app.id),
            application_id=app.id,
            actor_id=officer.id,
            action="OFFICER_APPLICATION_SCRUTINISED",
            previous_status=str(prev_app_status.value if hasattr(prev_app_status, "value") else prev_app_status),
            new_status=str(target_app_status.value),
            details={
                "reference_id": app.reference_id,
                "decision": decision_upper,
                "remarks": data.remarks,
                "verified_docs_count": sum(1 for d in documents if d.status == DocumentStatus.VERIFIED),
                "deficient_docs_count": sum(1 for d in documents if d.status == DocumentStatus.RESUBMISSION_REQUIRED),
                "rejected_docs_count": sum(1 for d in documents if d.status == DocumentStatus.REJECTED),
            },
        )

        if decision_upper == "DEFICIENT":
            self.audit_repo.log_event(
                entity_type="APPLICATION",
                entity_id=str(app.id),
                application_id=app.id,
                actor_id=officer.id,
                action="APPLICATION_MARKED_DEFICIENT",
                previous_status=str(prev_app_status.value if hasattr(prev_app_status, "value") else prev_app_status),
                new_status=str(target_app_status.value),
                details={
                    "deficiencies_created": len(created_deficiencies),
                    "note": "Ready for applicant resubmission in Phase 5",
                },
            )

        return app

    def get_stats(self, officer: User) -> OfficerStatsResponse:
        """
        Retrieves dashboard counters within the officer's jurisdiction.
        """
        scope = self._get_officer_scope(officer)
        if not scope["has_access"]:
            return OfficerStatsResponse(
                pending_review_count=0,
                verified_count=0,
                deficient_count=0,
                rejected_count=0,
                total_assigned_count=0,
            )

        query = self.db.query(Application).filter(Application.status != ApplicationStatus.DRAFT)

        if not scope["is_global"]:
            assignments = scope["assignments"]
            or_conditions = []
            for a in assignments:
                conds = []
                if a.scheme_id is not None:
                    conds.append(Application.scheme_id == a.scheme_id)
                if a.state is not None:
                    conds.append(
                        or_(
                            Application.form_data["personal"]["state"].astext == a.state,
                            Application.form_data["state"].astext == a.state,
                        )
                    )
                if conds:
                    or_conditions.append(and_(*conds))
            if or_conditions:
                query = query.filter(or_(*or_conditions))
            else:
                return OfficerStatsResponse(
                    pending_review_count=0,
                    verified_count=0,
                    deficient_count=0,
                    rejected_count=0,
                    total_assigned_count=0,
                )

        all_apps = query.all()
        pending = sum(1 for a in all_apps if a.status == ApplicationStatus.UNDER_MANUAL_REVIEW)
        verified = sum(1 for a in all_apps if a.status == ApplicationStatus.VERIFIED)
        deficient = sum(1 for a in all_apps if a.status == ApplicationStatus.DEFICIENT)
        rejected = sum(1 for a in all_apps if a.status == ApplicationStatus.REJECTED)

        return OfficerStatsResponse(
            pending_review_count=pending,
            verified_count=verified,
            deficient_count=deficient,
            rejected_count=rejected,
            total_assigned_count=len(all_apps),
        )

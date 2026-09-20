import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.enums import DocumentStatus, ApplicationStatus, AuditEntityType
from app.core.exceptions import EntityNotFoundException, InvalidOperationException
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.repositories.audit_repo import AuditRepository
from app.repositories.scheme_version_repo import SchemeVersionRepository
from app.services.ocr_service import BaseOCRService, LocalOCRService
from app.services.comparison_service import DocumentComparisonService

logger = logging.getLogger(__name__)


class DocumentVerificationService:
    """
    Orchestration service for Phase 3 document verification pipeline.
    Coordinates OCR extraction, normalizers, comparison engine,
    database record persistence, and granular audit logging.
    """

    def __init__(
        self,
        db: Session,
        ocr_service: Optional[BaseOCRService] = None,
        comparison_service: Optional[DocumentComparisonService] = None,
    ):
        self.db = db
        self.ocr_service = ocr_service or LocalOCRService()
        self.comparison_service = comparison_service or DocumentComparisonService()
        self.audit_repo = AuditRepository(db)
        self.scheme_version_repo = SchemeVersionRepository(db)

    def verify_document(
        self,
        document_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        force_rerun: bool = False,
    ) -> DocumentVerification:
        """
        Verifies a single document through OCR and comparison engine.
        Includes state-level idempotency guards.
        """
        doc = self.db.get(Document, document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found")

        # 1. Idempotency Check: if already processing and not a forced re-run
        if doc.status == DocumentStatus.PROCESSING and not force_rerun:
            existing = (
                self.db.query(DocumentVerification)
                .filter(DocumentVerification.document_id == document_id)
                .order_by(DocumentVerification.created_at.desc())
                .first()
            )
            if existing:
                return existing

        app = self.db.get(Application, doc.application_id)
        if not app:
            raise EntityNotFoundException("Associated application not found")

        # 2. Mark document as PROCESSING
        prev_doc_status = doc.status
        doc.status = DocumentStatus.PROCESSING
        self.db.commit()
        self.db.refresh(doc)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.DOCUMENT,
            entity_id=str(doc.id),
            application_id=app.id,
            actor_id=actor_id,
            action="DOCUMENT_OCR_STARTED",
            previous_status=str(prev_doc_status.value if hasattr(prev_doc_status, "value") else prev_doc_status),
            new_status=str(DocumentStatus.PROCESSING.value),
            details={
                "document_type": doc.document_type,
                "original_filename": doc.original_filename,
            },
        )

        # 3. Retrieve scheme version to get verification_fields
        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        verification_fields = []
        if version and version.required_documents:
            docs_list = version.required_documents.get("documents", [])
            for d_cfg in docs_list:
                code = d_cfg.get("code") or d_cfg.get("type")
                if code == doc.document_type:
                    verification_fields = d_cfg.get("verification_fields", [])
                    break

        # 4. Execute OCR Extraction
        ocr_result = self.ocr_service.extract_document(
            document_id=doc.id,
            file_path=Path(doc.storage_path),
            mime_type=doc.mime_type,
            document_type=doc.document_type,
        )

        comparison_results = {}
        flags = []
        is_verified = False

        if ocr_result.error:
            # OCR failed / engine missing / file corrupt -> FLAGGED (Never reject applicant)
            doc.status = DocumentStatus.FLAGGED
            flags.append({
                "field": "document",
                "label": doc.document_type,
                "application_value": None,
                "document_value": None,
                "reason": ocr_result.error,
                "severity": "HIGH",
            })
            self.audit_repo.log_event(
                entity_type=AuditEntityType.DOCUMENT,
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=actor_id,
                action="DOCUMENT_OCR_FAILED",
                previous_status=str(DocumentStatus.PROCESSING.value),
                new_status=str(DocumentStatus.FLAGGED.value),
                details={"error": ocr_result.error},
            )
        else:
            self.audit_repo.log_event(
                entity_type=AuditEntityType.DOCUMENT,
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=actor_id,
                action="DOCUMENT_OCR_COMPLETED",
                details={
                    "extracted_field_count": len(ocr_result.extracted_fields),
                    "overall_confidence": ocr_result.overall_confidence,
                    "is_scanned": ocr_result.is_scanned,
                },
            )

            self.audit_repo.log_event(
                entity_type=AuditEntityType.DOCUMENT,
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=actor_id,
                action="DOCUMENT_FIELDS_EXTRACTED",
                details={
                    "fields": list(ocr_result.extracted_fields.keys()),
                },
            )

            self.audit_repo.log_event(
                entity_type=AuditEntityType.DOCUMENT,
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=actor_id,
                action="DOCUMENT_VERIFICATION_STARTED",
                details={"verification_field_count": len(verification_fields)},
            )

            # 5. Run Comparison Engine
            comparison_results, flags, is_verified = self.comparison_service.compare_document_fields(
                application_form_data=app.form_data or {},
                extracted_fields=ocr_result.extracted_fields,
                verification_fields=verification_fields,
            )

            if is_verified:
                doc.status = DocumentStatus.VERIFIED
            else:
                doc.status = DocumentStatus.FLAGGED

        # 6. Upsert DocumentVerification record (Single authoritative representation)
        existing_verification = (
            self.db.query(DocumentVerification)
            .filter(DocumentVerification.document_id == document_id)
            .first()
        )

        extracted_fields_dict = {
            k: f.model_dump() for k, f in ocr_result.extracted_fields.items()
        }
        field_confidences_dict = {
            k: f.confidence for k, f in ocr_result.extracted_fields.items()
        }

        # Legacy compatibility dictionaries
        legacy_extracted_data = {
            k: f.value for k, f in ocr_result.extracted_fields.items()
        }
        legacy_matched = {
            k: v for k, v in comparison_results.items() if v.get("status") == "MATCH"
        }
        legacy_mismatched = {
            k: v for k, v in comparison_results.items() if v.get("status") == "MISMATCH"
        }

        now_utc = datetime.now(timezone.utc)

        if existing_verification:
            existing_verification.verification_status = doc.status.value
            existing_verification.ocr_text = ocr_result.raw_text
            existing_verification.extracted_fields = extracted_fields_dict
            existing_verification.field_confidences = field_confidences_dict
            existing_verification.comparison_results = comparison_results
            existing_verification.overall_confidence = ocr_result.overall_confidence
            existing_verification.flags = flags
            existing_verification.processed_at = now_utc
            existing_verification.extracted_data = legacy_extracted_data
            existing_verification.matched_fields = legacy_matched
            existing_verification.mismatched_fields = legacy_mismatched
            existing_verification.verified_by = actor_id
            existing_verification.verified_at = now_utc
            verification_rec = existing_verification
        else:
            verification_rec = DocumentVerification(
                document_id=doc.id,
                verification_status=doc.status.value,
                ocr_text=ocr_result.raw_text,
                extracted_fields=extracted_fields_dict,
                field_confidences=field_confidences_dict,
                comparison_results=comparison_results,
                overall_confidence=ocr_result.overall_confidence,
                flags=flags,
                processed_at=now_utc,
                extracted_data=legacy_extracted_data,
                matched_fields=legacy_matched,
                mismatched_fields=legacy_mismatched,
                verification_source="AI",
                verified_by=actor_id,
                verified_at=now_utc,
            )
            self.db.add(verification_rec)

        self.db.commit()
        self.db.refresh(doc)
        self.db.refresh(verification_rec)

        # 7. Audit completion and flags
        self.audit_repo.log_event(
            entity_type=AuditEntityType.DOCUMENT,
            entity_id=str(doc.id),
            application_id=app.id,
            actor_id=actor_id,
            action="DOCUMENT_VERIFICATION_COMPLETED",
            previous_status=str(DocumentStatus.PROCESSING.value),
            new_status=str(doc.status.value),
            details={
                "verification_status": doc.status.value,
                "flag_count": len(flags),
                "is_verified": is_verified,
            },
        )

        if flags:
            has_mismatch = any(f.get("severity") == "HIGH" for f in flags)
            action_name = "DOCUMENT_MISMATCH_DETECTED" if has_mismatch else "AI_VERIFICATION_FLAGGED"
            self.audit_repo.log_event(
                entity_type=AuditEntityType.DOCUMENT,
                entity_id=str(doc.id),
                application_id=app.id,
                actor_id=actor_id,
                action=action_name,
                details={
                    "flag_count": len(flags),
                    "flags": flags,
                },
            )

        return verification_rec

    def verify_application_documents(
        self,
        application_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        force_rerun: bool = False,
    ) -> Dict[str, Any]:
        """
        Orchestrates verification for all documents uploaded to an application.
        Strictly verifies scheme required documents before transitioning application
        status from UNDER_AI_VERIFICATION to UNDER_MANUAL_REVIEW.
        AI NEVER rejects the application.
        """
        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException(f"Application with ID {application_id} not found")

        version = None
        if app.scheme_version_id:
            version = self.scheme_version_repo.get_by_id(app.scheme_version_id)
        if not version:
            version = self.scheme_version_repo.get_active_version(app.scheme_id)

        # Process each current/active document (skip historical superseded versions)
        documents = [d for d in (app.documents or []) if getattr(d, "is_current", True)]
        verified_results = []
        for doc in documents:
            v_rec = self.verify_document(
                document_id=doc.id,
                actor_id=actor_id,
                force_rerun=force_rerun,
            )
            verified_results.append(v_rec)

        # Check completion criteria against scheme version
        all_required_present = True
        all_required_processed = True

        if version and version.required_documents:
            required_doc_configs = [
                d for d in version.required_documents.get("documents", [])
                if d.get("required", True)
            ]
            doc_map = {d.document_type: d for d in documents}

            for req in required_doc_configs:
                code = req.get("code") or req.get("type")
                uploaded_doc = doc_map.get(code)
                if not uploaded_doc:
                    all_required_present = False
                    break
                # Must be in a terminal state: VERIFIED or FLAGGED
                if uploaded_doc.status not in (DocumentStatus.VERIFIED, DocumentStatus.FLAGGED):
                    all_required_processed = False
                    break

        # Transition application if all required documents exist and are processed
        if all_required_present and all_required_processed and app.status == ApplicationStatus.UNDER_AI_VERIFICATION:
            prev_status = app.status
            app.status = ApplicationStatus.UNDER_MANUAL_REVIEW
            self.db.commit()
            self.db.refresh(app)

            verified_count = sum(1 for v in verified_results if v.verification_status == "VERIFIED")
            flagged_count = sum(1 for v in verified_results if v.verification_status == "FLAGGED")

            self.audit_repo.log_event(
                entity_type=AuditEntityType.APPLICATION,
                entity_id=str(app.id),
                application_id=app.id,
                actor_id=actor_id,
                action="APPLICATION_AI_VERIFICATION_COMPLETED",
                previous_status=str(prev_status.value),
                new_status=str(ApplicationStatus.UNDER_MANUAL_REVIEW.value),
                details={
                    "total_documents": len(documents),
                    "verified_count": verified_count,
                    "flagged_count": flagged_count,
                    "transition": "UNDER_MANUAL_REVIEW",
                    "note": "Ready for scrutiny by human verification officer (Phase 4)",
                },
            )

        return {
            "application_id": app.id,
            "status": app.status.value,
            "total_documents": len(documents),
            "verifications": verified_results,
        }

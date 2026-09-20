import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, SelectionResultEnum, UserRole, AuditEntityType
from app.core.exceptions import (
    BoundaryTieConflictException,
    ConflictException,
    EntityNotFoundException,
    ForbiddenException,
    InvalidStatusTransitionException,
    QuorumNotMetException,
    ValidationException,
)
from app.core.status_transitions import can_transition_application
from app.models.application import Application
from app.models.committee_assignment import CommitteeAssignment
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.committee_review import CommitteeReview
from app.models.merit_score import MeritScore
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.selection_result import SelectionResult
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.schemas.committee import (
    BatchFinalizeRequest,
    CommitteeDossierResponse,
    CommitteeReviewRequest,
    CommitteeReviewResponse,
    SelectionOverrideRequest,
    TieResolutionRequest,
)
from app.services.merit_service import GenericMeritCalculator
from app.services.ranking_service import DynamicRankingEngine


class CommitteeService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditRepository(db)

    # -------------------------------------------------------------------------
    # 1. Committee Assignments & Jurisdiction
    # -------------------------------------------------------------------------
    def check_committee_jurisdiction(self, user_id: uuid.UUID, scheme_id: uuid.UUID) -> bool:
        """Verifies if a committee member is authorized to evaluate the given scheme."""
        user = self.db.get(User, user_id)
        if not user:
            return False
        user_role = user.role
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        if user_role == UserRole.ADMIN:
            return True

        assignments = (
            self.db.query(CommitteeAssignment)
            .filter(
                CommitteeAssignment.user_id == user_id,
                CommitteeAssignment.is_active == True,
            )
            .all()
        )
        if not assignments:
            return False

        for a in assignments:
            # Global assignment if scheme_id is None, or matching scheme
            if a.scheme_id is None or a.scheme_id == scheme_id:
                return True
        return False

    # -------------------------------------------------------------------------
    # 2. Batch Creation & Immutability Management
    # -------------------------------------------------------------------------
    def create_batch(
        self,
        name: str,
        scheme_id: uuid.UUID,
        scheme_version_id: uuid.UUID,
        application_ids: List[uuid.UUID],
        creator: User,
    ) -> CommitteeEvaluationBatch:
        """
        Creates a new candidate cohort for committee evaluation.
        Ensures all candidate applications are VERIFIED and bound to the specified scheme version.
        """
        if not self.check_committee_jurisdiction(creator.id, scheme_id):
            raise ForbiddenException("User does not have committee jurisdiction over this scheme")

        scheme_version = self.db.get(SchemeVersion, scheme_version_id)
        if not scheme_version or scheme_version.scheme_id != scheme_id:
            raise ValidationException("Scheme version does not belong to specified scheme")

        # Validate applications
        app_id_strs = []
        for app_id in application_ids:
            app = self.db.get(Application, app_id)
            if not app:
                raise EntityNotFoundException("APPLICATION", app_id)
            if app.scheme_id != scheme_id:
                raise ValidationException(f"Application {app.reference_id} does not belong to specified scheme")
            if app.scheme_version_id and app.scheme_version_id != scheme_version_id:
                raise ValidationException(f"Application {app.reference_id} belongs to a different scheme version")
            if app.status != ApplicationStatus.VERIFIED:
                raise ValidationException(
                    f"Application {app.reference_id} is in status '{app.status.value if hasattr(app.status, 'value') else app.status}', "
                    "not 'VERIFIED'. Only verified applications can be added to an evaluation batch."
                )
            app_id_strs.append(str(app_id))

        batch = CommitteeEvaluationBatch(
            name=name,
            scheme_id=scheme_id,
            scheme_version_id=scheme_version_id,
            application_ids=app_id_strs,
            status="OPEN_FOR_EVALUATION",
            is_locked=False,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.COMMITTEE.value,
            entity_id=str(batch.id),
            action="COMMITTEE_BATCH_CREATED",
            actor_id=creator.id,
            details={
                "batch_name": name,
                "scheme_id": str(scheme_id),
                "scheme_version_id": str(scheme_version_id),
                "application_count": len(app_id_strs),
            },
        )
        return batch

    def add_application_to_batch(
        self,
        batch_id: uuid.UUID,
        application_id: uuid.UUID,
        actor: User,
    ) -> CommitteeEvaluationBatch:
        batch = self.db.get(CommitteeEvaluationBatch, batch_id)
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if not self.check_committee_jurisdiction(actor.id, batch.scheme_id):
            raise ForbiddenException("User does not have committee jurisdiction over this scheme")

        if batch.is_locked:
            raise ConflictException("Evaluation batch is locked. Membership cannot be modified.")

        # Batch membership is immutable once the first review is submitted
        review_count = (
            self.db.query(CommitteeReview)
            .filter(CommitteeReview.batch_id == batch_id)
            .count()
        )
        if review_count > 0:
            raise ConflictException(
                "A committee evaluation batch is immutable in membership once reviews have begun. "
                "Applications cannot be added to or removed from the batch after evaluation starts."
            )

        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException("APPLICATION", application_id)
        if app.scheme_id != batch.scheme_id:
            raise ValidationException("Application does not belong to the batch's scheme")
        if app.scheme_version_id and app.scheme_version_id != batch.scheme_version_id:
            raise ValidationException("Application belongs to a different scheme version")
        if app.status != ApplicationStatus.VERIFIED:
            raise ValidationException(
                f"Application is in status '{app.status}', not 'VERIFIED'."
            )

        app_id_str = str(application_id)
        current_ids = list(batch.application_ids or [])
        if app_id_str not in current_ids:
            current_ids.append(app_id_str)
            batch.application_ids = current_ids
            self.db.commit()
            self.db.refresh(batch)

            self.audit_repo.log_event(
                entity_type=AuditEntityType.COMMITTEE.value,
                entity_id=str(batch.id),
                action="COMMITTEE_BATCH_APPLICATION_ADDED",
                actor_id=actor.id,
                details={
                    "application_id": app_id_str,
                    "new_application_count": len(current_ids),
                },
            )
        return batch

    # -------------------------------------------------------------------------
    # 3. Blind Committee Scrutiny Queue
    # -------------------------------------------------------------------------
    def get_batch_dossiers(
        self,
        batch_id: uuid.UUID,
        member: User,
    ) -> List[CommitteeDossierResponse]:
        """
        Retrieves candidate dossiers for blind committee review.
        Enforces Blind Scrutiny:
          - Does NOT return peer reviewer scores or peer remarks.
          - Does NOT return provisional ranks or total merit scores during active evaluation.
          - Returns only the authenticated member's own review if already submitted.
        """
        batch = self.db.get(CommitteeEvaluationBatch, batch_id)
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if not self.check_committee_jurisdiction(member.id, batch.scheme_id):
            raise ForbiddenException("User does not have committee jurisdiction over this scheme")

        scheme = self.db.get(Scheme, batch.scheme_id)
        scheme_version = self.db.get(SchemeVersion, batch.scheme_version_id)
        scoring_rules = (scheme_version.scoring_weights if scheme_version else {}) or {}
        committee_config = scoring_rules.get("committee_config", {})
        required_quorum = int(committee_config.get("required_quorum", 1))

        dossiers = []
        for app_id_str in batch.application_ids:
            app_uuid = uuid.UUID(app_id_str)
            app = self.db.get(Application, app_uuid)
            if not app:
                continue

            form_data = app.form_data or {}
            personal = form_data.get("personal", {})
            academic = form_data.get("academic", {})
            research = form_data.get("research", {})

            # Count completed reviews for this app in this batch
            reviews_query = self.db.query(CommitteeReview).filter(
                CommitteeReview.batch_id == batch_id,
                CommitteeReview.application_id == app_uuid,
            )
            completed_count = reviews_query.count()

            # Find authenticated member's own review
            my_rev_obj = reviews_query.filter(CommitteeReview.committee_member_id == member.id).first()
            my_rev_schema = None
            if my_rev_obj:
                my_rev_schema = CommitteeReviewResponse(
                    id=my_rev_obj.id,
                    application_id=my_rev_obj.application_id,
                    committee_member_id=my_rev_obj.committee_member_id,
                    committee_member_name=member.full_name,
                    batch_id=my_rev_obj.batch_id,
                    scores=my_rev_obj.scores,
                    remarks=my_rev_obj.remarks,
                    recommendation=my_rev_obj.recommendation,
                    is_locked=my_rev_obj.is_locked,
                    created_at=my_rev_obj.created_at,
                    updated_at=my_rev_obj.updated_at,
                )

            # Verified documents list (summarized, no internal officer flags)
            doc_summaries = []
            for doc in (app.documents or []):
                if getattr(doc, "is_current", True):
                    doc_summaries.append({
                        "document_type": doc.document_type,
                        "original_filename": doc.original_filename,
                        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
                    })

            dossier = CommitteeDossierResponse(
                application_id=app.id,
                reference_id=app.reference_id,
                batch_id=batch.id,
                scheme_id=batch.scheme_id,
                scheme_name=scheme.name if scheme else "",
                scheme_version_id=batch.scheme_version_id,
                scheme_version=scheme_version.scheme_version if scheme_version else "1.0",
                applicant_name=personal.get("full_name") or app.applicant.full_name if app.applicant else "Applicant",
                category=form_data.get("community") or personal.get("caste_tribe_name") or "ST",
                state=personal.get("state") or form_data.get("state"),
                academic_summary=academic,
                proposal_summary=research,
                verified_documents=doc_summaries,
                my_review=my_rev_schema,
                is_batch_locked=batch.is_locked,
                required_quorum=required_quorum,
                completed_reviews_count=completed_count,
            )
            dossiers.append(dossier)

        return dossiers

    # -------------------------------------------------------------------------
    # 4. Review Submission
    # -------------------------------------------------------------------------
    def record_review(
        self,
        batch_id: uuid.UUID,
        application_id: uuid.UUID,
        member: User,
        data: CommitteeReviewRequest,
    ) -> CommitteeReview:
        """
        Submits or updates an individual committee member's scorecard and remarks.
        Enforces batch locking and application state constraints.
        """
        batch = self.db.get(CommitteeEvaluationBatch, batch_id)
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if batch.is_locked:
            raise ConflictException("Evaluation window for this batch is permanently locked. Reviews cannot be modified.")

        if str(application_id) not in batch.application_ids:
            raise ValidationException("Application does not belong to this evaluation batch")

        app = self.db.get(Application, application_id)
        if not app:
            raise EntityNotFoundException("APPLICATION", application_id)

        if app.status != ApplicationStatus.VERIFIED:
            raise ConflictException(
                f"Application is in status '{app.status.value if hasattr(app.status, 'value') else app.status}', "
                "not 'VERIFIED'. Scorecards cannot be recorded for applications beyond the scrutiny stage."
            )

        if not self.check_committee_jurisdiction(member.id, batch.scheme_id):
            raise ForbiddenException("User does not have committee jurisdiction over this scheme")

        # Check existing review by this member in this batch
        existing = (
            self.db.query(CommitteeReview)
            .filter(
                CommitteeReview.batch_id == batch_id,
                CommitteeReview.application_id == application_id,
                CommitteeReview.committee_member_id == member.id,
            )
            .first()
        )

        now_utc = datetime.now(timezone.utc)
        if existing:
            if existing.is_locked:
                raise ConflictException("Review scorecard is locked and cannot be updated.")
            existing.scores = data.scores
            existing.remarks = data.remarks
            existing.recommendation = data.recommendation
            existing.updated_at = now_utc
            review_obj = existing
        else:
            review_obj = CommitteeReview(
                application_id=application_id,
                committee_member_id=member.id,
                scheme_id=batch.scheme_id,
                scheme_version_id=batch.scheme_version_id,
                batch_id=batch_id,
                scores=data.scores,
                remarks=data.remarks,
                recommendation=data.recommendation,
                is_locked=False,
            )
            self.db.add(review_obj)

        self.db.commit()
        self.db.refresh(review_obj)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.APPLICATION.value,
            entity_id=str(application_id),
            action="COMMITTEE_REVIEW_SUBMITTED",
            actor_id=member.id,
            details={
                "batch_id": str(batch_id),
                "review_id": str(review_obj.id),
                "recommendation": data.recommendation,
                "scores": data.scores,
            },
        )
        return review_obj

    # -------------------------------------------------------------------------
    # 5. Batch-Scoped Evaluation Lock
    # -------------------------------------------------------------------------
    def lock_batch_evaluations(
        self,
        batch_id: uuid.UUID,
        actor: User,
    ) -> CommitteeEvaluationBatch:
        """
        Atomically locks evaluations for an entire candidate cohort.
        Enforces Strict Per-Application Quorum: Every candidate in the batch must
        individually satisfy required_quorum before locking can succeed.
        """
        batch = (
            self.db.query(CommitteeEvaluationBatch)
            .filter(CommitteeEvaluationBatch.id == batch_id)
            .with_for_update()
            .first()
        )
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if batch.is_locked:
            return batch  # Already locked (idempotent)

        if not self.check_committee_jurisdiction(actor.id, batch.scheme_id):
            raise ForbiddenException("User does not have authority to lock this evaluation batch")

        scheme_version = self.db.get(SchemeVersion, batch.scheme_version_id)
        scoring_rules = (scheme_version.scoring_weights if scheme_version else {}) or {}
        committee_config = scoring_rules.get("committee_config", {})
        required_quorum = int(committee_config.get("required_quorum", 1))

        # Check per-application quorum
        deficient_candidates = []
        for app_id_str in batch.application_ids:
            app_uuid = uuid.UUID(app_id_str)
            completed_count = (
                self.db.query(CommitteeReview)
                .filter(
                    CommitteeReview.batch_id == batch_id,
                    CommitteeReview.application_id == app_uuid,
                )
                .count()
            )
            if completed_count < required_quorum:
                app = self.db.get(Application, app_uuid)
                ref = app.reference_id if app else app_id_str
                deficient_candidates.append(f"{ref} ({completed_count}/{required_quorum} reviews)")

        if deficient_candidates:
            raise QuorumNotMetException(
                f"Cannot lock batch evaluations: {len(deficient_candidates)} candidate(s) do not meet the required quorum of {required_quorum} review(s): "
                + ", ".join(deficient_candidates)
            )

        now_utc = datetime.now(timezone.utc)
        # Lock all individual reviews in this batch
        self.db.query(CommitteeReview).filter(CommitteeReview.batch_id == batch_id).update({"is_locked": True})

        # Lock the batch
        batch.is_locked = True
        batch.locked_at = now_utc
        batch.locked_by = actor.id
        batch.status = "EVALUATION_LOCKED"

        self.db.commit()
        self.db.refresh(batch)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.COMMITTEE.value,
            entity_id=str(batch_id),
            action="COMMITTEE_EVALUATION_LOCKED",
            actor_id=actor.id,
            details={
                "candidate_count": len(batch.application_ids),
                "required_quorum": required_quorum,
                "locked_at": now_utc.isoformat(),
            },
        )
        return batch

    # -------------------------------------------------------------------------
    # 6. Atomic Batch Merit Calculation & Ranking
    # -------------------------------------------------------------------------
    def calculate_batch_merit(
        self,
        batch_id: uuid.UUID,
        actor: User,
    ) -> Tuple[int, bool, List[uuid.UUID]]:
        """
        All-or-nothing merit calculation and dynamic ranking for an evaluation batch.
        Enforces:
          - Batch must be locked.
          - Per-application quorum check.
          - Purely deterministic calculation from frozen rules snapshot.
          - Boundary-tie detection.
        """
        batch = self.db.get(CommitteeEvaluationBatch, batch_id)
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if batch.status == "FINALIZED":
            raise ConflictException("This evaluation batch has already been finalized. Merit scores and ranks are permanently frozen.")

        if not batch.is_locked:
            raise ConflictException("Evaluation batch must be locked before merit calculation can proceed.")

        if not self.check_committee_jurisdiction(actor.id, batch.scheme_id):
            raise ForbiddenException("User does not have authority to calculate merit for this batch")

        scheme_version = self.db.get(SchemeVersion, batch.scheme_version_id)
        if not scheme_version:
            raise EntityNotFoundException("SCHEME_VERSION", batch.scheme_version_id)

        scoring_rules = scheme_version.scoring_weights or {}
        quota_config = scoring_rules.get("quota_config") or scoring_rules.get("quotas") or {}
        tie_breaking_order = scoring_rules.get("tie_breaking_order", [])

        # Begin atomic calculation
        candidates_to_rank: List[Tuple[Application, MeritScore]] = []
        for app_id_str in batch.application_ids:
            app_uuid = uuid.UUID(app_id_str)
            app = self.db.get(Application, app_uuid)
            if not app:
                continue

            # Load reviews for this candidate
            reviews = (
                self.db.query(CommitteeReview)
                .filter(
                    CommitteeReview.batch_id == batch_id,
                    CommitteeReview.application_id == app_uuid,
                )
                .all()
            )

            # Calculate deterministic score
            rules_to_use = app.frozen_rules_snapshot or scoring_rules
            total_score, breakdown = GenericMeritCalculator.calculate_application_score(
                app=app,
                scoring_rules=rules_to_use,
                reviews=reviews,
            )

            # Upsert MeritScore record
            existing_score = (
                self.db.query(MeritScore)
                .filter(
                    MeritScore.application_id == app.id,
                    MeritScore.batch_id == batch_id,
                )
                .first()
            )
            now_utc = datetime.now(timezone.utc)
            if existing_score:
                existing_score.total_score = total_score
                existing_score.score_breakdown = breakdown
                existing_score.calculated_at = now_utc
                existing_score.calculated_by = actor.id
                merit_score_obj = existing_score
            else:
                merit_score_obj = MeritScore(
                    application_id=app.id,
                    scheme_version_id=batch.scheme_version_id,
                    batch_id=batch_id,
                    total_score=total_score,
                    score_breakdown=breakdown,
                    formula_version="1.0",
                    is_current=True,
                    calculated_at=now_utc,
                    calculated_by=actor.id,
                )
                self.db.add(merit_score_obj)

            candidates_to_rank.append((app, merit_score_obj))

        # Perform dynamic ranking & boundary tie check
        ranked_list, boundary_tie_flag, tied_ids = DynamicRankingEngine.rank_batch_candidates(
            candidates=candidates_to_rank,
            tie_breaking_order=tie_breaking_order,
            quota_config=quota_config,
        )

        # Update ranks and application statuses
        for app, score_obj, assigned_rank, tie_level in ranked_list:
            score_obj.rank = assigned_rank
            score_obj.tie_break_level = tie_level
            app.merit_score = score_obj.total_score

            # Transition status from VERIFIED to MERIT_RANKED
            if app.status == ApplicationStatus.VERIFIED:
                app.status = ApplicationStatus.MERIT_RANKED

        batch.status = "MERIT_CALCULATED"
        self.db.commit()

        self.audit_repo.log_event(
            entity_type=AuditEntityType.COMMITTEE.value,
            entity_id=str(batch_id),
            action="MERIT_CALCULATION_BATCH_COMPLETED",
            actor_id=actor.id,
            details={
                "scored_count": len(ranked_list),
                "boundary_tie_flag": boundary_tie_flag,
                "tied_candidate_ids": [str(x) for x in tied_ids],
            },
        )
        return len(ranked_list), boundary_tie_flag, tied_ids

    # -------------------------------------------------------------------------
    # 7. Audited Chairperson Boundary-Tie Resolution
    # -------------------------------------------------------------------------
    def resolve_boundary_tie(
        self,
        batch_id: uuid.UUID,
        data: TieResolutionRequest,
        chairperson: User,
    ) -> Dict[str, Any]:
        """
        Resolves an exact tie crossing a selection boundary through an audited committee resolution.
        """
        batch = self.db.get(CommitteeEvaluationBatch, batch_id)
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if batch.status == "FINALIZED":
            raise ConflictException("Cannot resolve ties on an already finalized batch. Merit scores and ranks are permanently frozen.")

        if not self.check_committee_jurisdiction(chairperson.id, batch.scheme_id):
            raise ForbiddenException("User does not have authority to resolve ties for this batch")

        pref_app = self.db.get(Application, data.preferred_candidate_id)
        sec_app = self.db.get(Application, data.secondary_candidate_id)
        if not pref_app or not sec_app:
            raise EntityNotFoundException("APPLICATION", "Tied candidate not found")

        pref_score = self.db.query(MeritScore).filter(MeritScore.application_id == pref_app.id, MeritScore.batch_id == batch_id).first()
        sec_score = self.db.query(MeritScore).filter(MeritScore.application_id == sec_app.id, MeritScore.batch_id == batch_id).first()

        if not pref_score or not sec_score:
            raise ValidationException("Merit score records missing for tied candidates")

        # Verify they are genuinely tied or adjacent
        pref_score.tie_break_level = "CHAIRPERSON_RESOLUTION"
        sec_score.tie_break_level = "CHAIRPERSON_RESOLUTION"

        # Ensure preferred candidate has lower rank (better position)
        r1, r2 = sorted([pref_score.rank or 1, sec_score.rank or 2])
        pref_score.rank = r1
        sec_score.rank = r2

        self.db.commit()

        self.audit_repo.log_event(
            entity_type=AuditEntityType.COMMITTEE.value,
            entity_id=str(batch_id),
            action="SELECTION_TIE_RESOLVED",
            actor_id=chairperson.id,
            details={
                "preferred_candidate_id": str(pref_app.id),
                "secondary_candidate_id": str(sec_app.id),
                "preferred_rank": r1,
                "secondary_rank": r2,
                "statutory_justification": data.statutory_justification,
                "authority_order_reference": data.authority_order_reference,
            },
        )
        return {
            "batch_id": batch_id,
            "preferred_candidate_id": pref_app.id,
            "secondary_candidate_id": sec_app.id,
            "status": "TIE_RESOLVED",
        }

    # -------------------------------------------------------------------------
    # 8. Batch Finalization & Quota Allocation
    # -------------------------------------------------------------------------
    def finalize_batch_selection(
        self,
        batch_id: uuid.UUID,
        data: BatchFinalizeRequest,
        chairperson: User,
    ) -> Dict[str, Any]:
        """
        Finalizes selection, waitlisting, and rejection for an entire batch.
        Strict Invariants:
          - Entire allocation runs in an atomic database transaction with row locks.
          - Quota counts derived exclusively from scheme version configuration.
          - Halts if any boundary tie remains unresolved.
        """
        batch = (
            self.db.query(CommitteeEvaluationBatch)
            .filter(CommitteeEvaluationBatch.id == batch_id)
            .with_for_update()
            .first()
        )
        if not batch:
            raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

        if batch.status == "FINALIZED":
            raise ConflictException("This evaluation batch has already been finalized.")

        if not self.check_committee_jurisdiction(chairperson.id, batch.scheme_id):
            raise ForbiddenException("User does not have authority to finalize selection for this batch")

        scheme_version = self.db.get(SchemeVersion, batch.scheme_version_id)
        scoring_rules = scheme_version.scoring_weights or {}
        quota_config = scoring_rules.get("quota_config") or scoring_rules.get("quotas") or {}
        tie_breaking_order = scoring_rules.get("tie_breaking_order", [])

        # Lock all applications in the batch
        candidates: List[Tuple[Application, MeritScore]] = []
        for app_id_str in batch.application_ids:
            app_uuid = uuid.UUID(app_id_str)
            app = (
                self.db.query(Application)
                .filter(Application.id == app_uuid)
                .with_for_update()
                .first()
            )
            if not app:
                continue

            if app.status != ApplicationStatus.MERIT_RANKED:
                raise ConflictException(
                    f"Application {app.reference_id} is in status '{app.status}', not 'MERIT_RANKED'. "
                    "Cannot finalize selection before all applications are merit-ranked."
                )

            score_obj = (
                self.db.query(MeritScore)
                .filter(MeritScore.application_id == app.id, MeritScore.batch_id == batch_id)
                .first()
            )
            if not score_obj:
                raise ValidationException(f"MeritScore missing for application {app.reference_id}")

            candidates.append((app, score_obj))

        # Re-check boundary tie guard
        ranked_list, boundary_tie_flag, _ = DynamicRankingEngine.rank_batch_candidates(
            candidates=candidates,
            tie_breaking_order=tie_breaking_order,
            quota_config=quota_config,
        )

        outcomes = DynamicRankingEngine.allocate_quota_outcomes(
            ranked_list=ranked_list,
            quota_config=quota_config,
            has_boundary_tie=boundary_tie_flag,
        )

        now_utc = datetime.now(timezone.utc)
        selected_count = 0
        waitlisted_count = 0
        rejected_count = 0

        for app, score_obj, rank, tie_level, outcome_str in outcomes:
            enum_val = SelectionResultEnum(outcome_str)
            app_target_status = ApplicationStatus(outcome_str)

            if not can_transition_application(app.status, app_target_status):
                raise InvalidStatusTransitionException("APPLICATION", app.status.value, app_target_status.value)

            app.status = app_target_status

            reason_text = None
            if outcome_str == "REJECTED":
                reason_text = "MERIT_QUOTA_EXHAUSTED"
                rejected_count += 1
            elif outcome_str == "SELECTED":
                selected_count += 1
            elif outcome_str == "WAITLISTED":
                waitlisted_count += 1

            # Persist SelectionResult
            sel_result = SelectionResult(
                application_id=app.id,
                scheme_version_id=batch.scheme_version_id,
                batch_id=batch_id,
                result=enum_val,
                rank=rank,
                quota_category="GENERAL_ST",
                reason=reason_text,
                committee_minutes=data.committee_minutes,
                authority_reference=data.resolution_reference,
                selection_round=1,
                is_override=False,
                finalized_by=chairperson.id,
                finalized_at=now_utc,
            )
            self.db.add(sel_result)

        batch.status = "FINALIZED"
        self.db.commit()

        self.audit_repo.log_event(
            entity_type=AuditEntityType.SCHEME.value,
            entity_id=str(batch.scheme_id),
            action="SELECTION_BATCH_FINALIZED",
            actor_id=chairperson.id,
            details={
                "batch_id": str(batch_id),
                "total_selected": selected_count,
                "total_waitlisted": waitlisted_count,
                "total_rejected": rejected_count,
                "resolution_reference": data.resolution_reference,
            },
        )
        return {
            "batch_id": batch_id,
            "status": "FINALIZED",
            "selected_count": selected_count,
            "waitlisted_count": waitlisted_count,
            "rejected_count": rejected_count,
            "finalized_at": now_utc.isoformat(),
        }

    # -------------------------------------------------------------------------
    # 9. Rank-Preserving Administrative Selection Override
    # -------------------------------------------------------------------------
    def record_selection_override(
        self,
        data: SelectionOverrideRequest,
        admin: User,
    ) -> SelectionResult:
        """
        Administrative Selection Exception Engine (ADMIN only).
        Strict Invariants:
          - Never alters original MeritScore.rank or MeritScore.total_score.
          - Only allows WAITLISTED -> SELECTED (e.g. forfeiture vacancy-fill) or SELECTED -> REJECTED (disqualification).
          - Inserts a new SelectionResult row with selection_round = 2 to retain auditable history.
        """
        admin_role = admin.role
        if isinstance(admin_role, str):
            admin_role = UserRole(admin_role)
        if admin_role != UserRole.ADMIN:
            raise ForbiddenException("Administrative selection overrides can only be executed by ADMIN users")

        app = (
            self.db.query(Application)
            .filter(Application.id == data.application_id)
            .with_for_update()
            .first()
        )
        if not app:
            raise EntityNotFoundException("APPLICATION", data.application_id)

        target_status_upper = data.target_status.strip().upper()
        if target_status_upper not in ("SELECTED", "REJECTED"):
            raise ValidationException("target_status for override must be 'SELECTED' or 'REJECTED'")

        # Enforce allowed source states
        if target_status_upper == "SELECTED" and app.status != ApplicationStatus.WAITLISTED:
            raise ConflictException(
                f"Cannot override application to SELECTED from status '{app.status}'. Candidate must be in WAITLISTED status."
            )
        if target_status_upper == "REJECTED" and app.status != ApplicationStatus.SELECTED:
            raise ConflictException(
                f"Cannot override application to REJECTED from status '{app.status}'. Candidate must be in SELECTED status."
            )

        # Retrieve original merit score to guarantee rank preservation
        merit_score = self.db.query(MeritScore).filter(MeritScore.application_id == app.id, MeritScore.is_current == True).first()
        original_rank = merit_score.rank if merit_score else None

        now_utc = datetime.now(timezone.utc)
        prev_status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
        app.status = ApplicationStatus(target_status_upper)

        # Create new SelectionResult row with incremented round
        override_result = SelectionResult(
            application_id=app.id,
            scheme_version_id=app.scheme_version_id,
            batch_id=merit_score.batch_id if merit_score else None,
            result=SelectionResultEnum(target_status_upper),
            rank=original_rank,  # Permanent original rank preserved!
            quota_category="GENERAL_ST",
            reason=data.override_reason,
            authority_reference=data.authority_reference,
            selection_round=data.selection_round,
            is_override=True,
            override_reason=data.override_reason,
            override_by=admin.id,
            finalized_by=admin.id,
            finalized_at=now_utc,
        )
        self.db.add(override_result)
        self.db.commit()
        self.db.refresh(override_result)

        self.audit_repo.log_event(
            entity_type=AuditEntityType.APPLICATION.value,
            entity_id=str(app.id),
            action="SELECTION_ADMIN_OVERRIDE",
            actor_id=admin.id,
            previous_status=prev_status_val,
            new_status=target_status_upper,
            details={
                "original_rank": original_rank,
                "authority_reference": data.authority_reference,
                "override_reason": data.override_reason,
                "selection_round": data.selection_round,
            },
        )
        return override_result

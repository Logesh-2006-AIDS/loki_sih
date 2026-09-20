import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, check_committee_scheme_scope
from app.core.enums import UserRole, ApplicationStatus
from app.core.exceptions import ForbiddenException, EntityNotFoundException
from app.models.application import Application
from app.models.committee_assignment import CommitteeAssignment
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.committee_review import CommitteeReview
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.selection_result import SelectionResult
from app.models.user import User
from app.schemas.committee import (
    BatchAddApplicationRequest,
    BatchFinalizeRequest,
    CommitteeAssignmentCreate,
    CommitteeAssignmentResponse,
    CommitteeBatchCreate,
    CommitteeBatchResponse,
    CommitteeDossierResponse,
    CommitteeReviewRequest,
    CommitteeReviewResponse,
    SelectionOverrideRequest,
    SelectionResultResponse,
    TieResolutionRequest,
)
from app.services.committee_service import CommitteeService

router = APIRouter()


# -----------------------------------------------------------------------------
# Schemes & Workload Counters
# -----------------------------------------------------------------------------
@router.get(
    "/schemes",
    summary="Get schemes assigned to current committee member with workload counters",
)
def get_committee_schemes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
) -> List[Dict[str, Any]]:
    # Get active schemes in the system
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    all_schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
    results = []

    for s in all_schemes:
        if not check_committee_scheme_scope(db, current_user.id, s.id):
            continue

        active_version = db.query(SchemeVersion).filter(SchemeVersion.scheme_id == s.id, SchemeVersion.is_active == True).first()
        version_id = active_version.id if active_version else None
        scoring_rules = (active_version.scoring_weights if active_version else {}) or {}
        committee_config = scoring_rules.get("committee_config", {})
        required_quorum = int(committee_config.get("required_quorum", 1))

        # Count verified applications
        verified_count = (
            db.query(Application)
            .filter(
                Application.scheme_id == s.id,
                Application.status == ApplicationStatus.VERIFIED,
            )
            .count()
        )
        ranked_count = (
            db.query(Application)
            .filter(
                Application.scheme_id == s.id,
                Application.status == ApplicationStatus.MERIT_RANKED,
            )
            .count()
        )
        finalized_count = (
            db.query(Application)
            .filter(
                Application.scheme_id == s.id,
                Application.status.in_([ApplicationStatus.SELECTED, ApplicationStatus.WAITLISTED, ApplicationStatus.REJECTED]),
            )
            .count()
        )
        batches_count = (
            db.query(CommitteeEvaluationBatch)
            .filter(CommitteeEvaluationBatch.scheme_id == s.id)
            .count()
        )

        results.append({
            "scheme_id": s.id,
            "scheme_code": s.scheme_code,
            "scheme_name": s.name,
            "scheme_version_id": version_id,
            "scheme_version": active_version.scheme_version if active_version else "1.0",
            "is_demo": active_version.is_demo if active_version else True,
            "required_quorum": required_quorum,
            "verified_applications_count": verified_count,
            "merit_ranked_count": ranked_count,
            "finalized_count": finalized_count,
            "batches_count": batches_count,
        })

    return results


# -----------------------------------------------------------------------------
# Batch Management
# -----------------------------------------------------------------------------
@router.post(
    "/batches",
    response_model=CommitteeBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate evaluation batch (cohort)",
)
def create_batch(
    data: CommitteeBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    batch = service.create_batch(
        name=data.name,
        scheme_id=data.scheme_id,
        scheme_version_id=data.scheme_version_id,
        application_ids=data.application_ids,
        creator=current_user,
    )
    return CommitteeBatchResponse(
        id=batch.id,
        name=batch.name,
        scheme_id=batch.scheme_id,
        scheme_version_id=batch.scheme_version_id,
        status=batch.status,
        is_locked=batch.is_locked,
        locked_at=batch.locked_at,
        locked_by=batch.locked_by,
        application_count=len(batch.application_ids),
        reviews_completed_count=db.query(CommitteeReview).filter(CommitteeReview.batch_id == batch.id).count(),
        created_at=batch.created_at,
    )


@router.get(
    "/batches",
    response_model=List[CommitteeBatchResponse],
    summary="List committee evaluation batches",
)
def list_batches(
    scheme_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    query = db.query(CommitteeEvaluationBatch)
    if scheme_id:
        query = query.filter(CommitteeEvaluationBatch.scheme_id == scheme_id)

    batches = query.order_by(CommitteeEvaluationBatch.created_at.desc()).all()
    out = []
    for b in batches:
        if not check_committee_scheme_scope(db, current_user.id, b.scheme_id):
            continue
        reviews_count = db.query(CommitteeReview).filter(CommitteeReview.batch_id == b.id).count()
        out.append(
            CommitteeBatchResponse(
                id=b.id,
                name=b.name,
                scheme_id=b.scheme_id,
                scheme_version_id=b.scheme_version_id,
                status=b.status,
                is_locked=b.is_locked,
                locked_at=b.locked_at,
                locked_by=b.locked_by,
                application_count=len(b.application_ids),
                reviews_completed_count=reviews_count,
                created_at=b.created_at,
            )
        )
    return out


@router.get(
    "/batches/{batch_id}",
    response_model=CommitteeBatchResponse,
    summary="Get details of an evaluation batch",
)
def get_batch_details(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    b = db.get(CommitteeEvaluationBatch, batch_id)
    if not b:
        raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)
    if not check_committee_scheme_scope(db, current_user.id, b.scheme_id):
        raise ForbiddenException("User does not have committee jurisdiction over this scheme")

    reviews_count = db.query(CommitteeReview).filter(CommitteeReview.batch_id == b.id).count()
    return CommitteeBatchResponse(
        id=b.id,
        name=b.name,
        scheme_id=b.scheme_id,
        scheme_version_id=b.scheme_version_id,
        status=b.status,
        is_locked=b.is_locked,
        locked_at=b.locked_at,
        locked_by=b.locked_by,
        application_count=len(b.application_ids),
        reviews_completed_count=reviews_count,
        created_at=b.created_at,
    )


@router.post(
    "/batches/{batch_id}/applications",
    response_model=CommitteeBatchResponse,
    summary="Add an application to a draft evaluation batch",
)
def add_application_to_batch(
    batch_id: uuid.UUID,
    data: BatchAddApplicationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    batch = service.add_application_to_batch(
        batch_id=batch_id,
        application_id=data.application_id,
        actor=current_user,
    )
    reviews_count = db.query(CommitteeReview).filter(CommitteeReview.batch_id == batch.id).count()
    return CommitteeBatchResponse(
        id=batch.id,
        name=batch.name,
        scheme_id=batch.scheme_id,
        scheme_version_id=batch.scheme_version_id,
        status=batch.status,
        is_locked=batch.is_locked,
        locked_at=batch.locked_at,
        locked_by=batch.locked_by,
        application_count=len(batch.application_ids),
        reviews_completed_count=reviews_count,
        created_at=batch.created_at,
    )



# -----------------------------------------------------------------------------
# Blind Scrutiny Queue & Review Submission
# -----------------------------------------------------------------------------
@router.get(
    "/batches/{batch_id}/applications",
    response_model=List[CommitteeDossierResponse],
    summary="Get blind candidate dossiers for a batch",
)
def get_batch_applications(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    return service.get_batch_dossiers(batch_id=batch_id, member=current_user)


@router.post(
    "/applications/{application_id}/review",
    response_model=CommitteeReviewResponse,
    summary="Submit or update independent committee member review scorecard",
)
def submit_committee_review(
    application_id: uuid.UUID,
    data: CommitteeReviewRequest,
    batch_id: uuid.UUID = Query(..., description="Evaluation batch ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    rev = service.record_review(
        batch_id=batch_id,
        application_id=application_id,
        member=current_user,
        data=data,
    )
    return CommitteeReviewResponse(
        id=rev.id,
        application_id=rev.application_id,
        committee_member_id=rev.committee_member_id,
        committee_member_name=current_user.full_name,
        batch_id=rev.batch_id,
        scores=rev.scores,
        remarks=rev.remarks,
        recommendation=rev.recommendation,
        is_locked=rev.is_locked,
        created_at=rev.created_at,
        updated_at=rev.updated_at,
    )


@router.get(
    "/applications/{application_id}/reviews",
    response_model=List[CommitteeReviewResponse],
    summary="Get all submitted member reviews for an application (Post-Lock or Admin only)",
)
def get_application_reviews(
    application_id: uuid.UUID,
    batch_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    batch = db.get(CommitteeEvaluationBatch, batch_id)
    if not batch:
        raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    # Enforce Blind Review Protection: Committee members cannot see peer reviews while batch is unlocked!
    if not batch.is_locked and user_role != UserRole.ADMIN:
        raise ForbiddenException("Peer committee reviews are sealed until the evaluation batch is locked.")

    reviews = (
        db.query(CommitteeReview)
        .filter(
            CommitteeReview.application_id == application_id,
            CommitteeReview.batch_id == batch_id,
        )
        .all()
    )
    out = []
    for r in reviews:
        member = db.get(User, r.committee_member_id)
        out.append(
            CommitteeReviewResponse(
                id=r.id,
                application_id=r.application_id,
                committee_member_id=r.committee_member_id,
                committee_member_name=member.full_name if member else "Committee Member",
                batch_id=r.batch_id,
                scores=r.scores,
                remarks=r.remarks,
                recommendation=r.recommendation,
                is_locked=r.is_locked,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return out


# -----------------------------------------------------------------------------
# Batch Evaluation Locking & Tie Resolution
# -----------------------------------------------------------------------------
@router.post(
    "/batches/{batch_id}/lock-evaluations",
    response_model=CommitteeBatchResponse,
    summary="Atomically lock batch evaluations after validating per-application quorum",
)
def lock_batch_evaluations(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    batch = service.lock_batch_evaluations(batch_id=batch_id, actor=current_user)
    reviews_count = db.query(CommitteeReview).filter(CommitteeReview.batch_id == batch.id).count()
    return CommitteeBatchResponse(
        id=batch.id,
        name=batch.name,
        scheme_id=batch.scheme_id,
        scheme_version_id=batch.scheme_version_id,
        status=batch.status,
        is_locked=batch.is_locked,
        locked_at=batch.locked_at,
        locked_by=batch.locked_by,
        application_count=len(batch.application_ids),
        reviews_completed_count=reviews_count,
        created_at=batch.created_at,
    )


@router.post(
    "/batches/{batch_id}/resolve-tie",
    summary="Chairperson resolution for exact tie crossing quota boundary",
)
def resolve_boundary_tie(
    batch_id: uuid.UUID,
    data: TieResolutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    return service.resolve_boundary_tie(
        batch_id=batch_id,
        data=data,
        chairperson=current_user,
    )


# -----------------------------------------------------------------------------
# Batch Finalization
# -----------------------------------------------------------------------------
@router.post(
    "/batches/{batch_id}/finalize",
    summary="Finalize selection, waitlisting, and rejection for an entire batch",
)
def finalize_batch(
    batch_id: uuid.UUID,
    data: BatchFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    return service.finalize_batch_selection(
        batch_id=batch_id,
        data=data,
        chairperson=current_user,
    )


@router.get(
    "/batches/{batch_id}/results",
    response_model=List[SelectionResultResponse],
    summary="Get finalized selection outcomes for a batch",
)
def get_batch_results(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    batch = db.get(CommitteeEvaluationBatch, batch_id)
    if not batch:
        raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

    if not check_committee_scheme_scope(db, current_user.id, batch.scheme_id):
        raise ForbiddenException("User does not have committee jurisdiction over this scheme")

    results = (
        db.query(SelectionResult)
        .filter(SelectionResult.batch_id == batch_id)
        .order_by(SelectionResult.rank.asc().nullslast())
        .all()
    )
    return results


# -----------------------------------------------------------------------------
# Administrative Selection Override (ADMIN Only)
# -----------------------------------------------------------------------------
@router.post(
    "/admin/selection-override",
    response_model=SelectionResultResponse,
    summary="Administrative selection override with permanent rank preservation (ADMIN only)",
)
def administrative_selection_override(
    data: SelectionOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    service = CommitteeService(db)
    res = service.record_selection_override(data=data, admin=current_user)
    return res

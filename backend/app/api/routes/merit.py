import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, check_committee_scheme_scope
from app.core.enums import UserRole
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.application import Application
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.merit_score import MeritScore
from app.models.user import User
from app.schemas.merit import (
    MeritCalculationBatchResponse,
    MeritRankItem,
    MeritScoreResponse,
)
from app.services.committee_service import CommitteeService

router = APIRouter()


@router.post(
    "/batches/{batch_id}/calculate",
    response_model=MeritCalculationBatchResponse,
    summary="Execute all-or-nothing merit calculation and dynamic ranking for an evaluation batch",
)
def calculate_batch_merit(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    service = CommitteeService(db)
    scored_count, boundary_tie_flag, tied_ids = service.calculate_batch_merit(
        batch_id=batch_id,
        actor=current_user,
    )
    batch = db.get(CommitteeEvaluationBatch, batch_id)
    return MeritCalculationBatchResponse(
        batch_id=batch_id,
        scheme_id=batch.scheme_id,
        scheme_version_id=batch.scheme_version_id,
        scored_count=scored_count,
        status=batch.status,
        calculation_timestamp=datetime.now(timezone.utc),
        boundary_tie_flag=boundary_tie_flag,
        tied_candidate_ids=tied_ids,
    )


@router.get(
    "/batches/{batch_id}/ranking",
    response_model=List[MeritRankItem],
    summary="Get consolidated merit ranking list for an evaluation batch",
)
def get_batch_ranking(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    batch = db.get(CommitteeEvaluationBatch, batch_id)
    if not batch:
        raise EntityNotFoundException("COMMITTEE_BATCH", batch_id)

    if not check_committee_scheme_scope(db, current_user.id, batch.scheme_id):
        raise ForbiddenException("User does not have committee jurisdiction over this scheme")

    scores = (
        db.query(MeritScore)
        .filter(MeritScore.batch_id == batch_id, MeritScore.is_current == True)
        .order_by(MeritScore.rank.asc().nullslast())
        .all()
    )

    out = []
    for s in scores:
        app = db.get(Application, s.application_id)
        if not app:
            continue
        applicant_name = "Applicant"
        if app.applicant and app.applicant.full_name:
            applicant_name = app.applicant.full_name
        elif (app.form_data or {}).get("personal", {}).get("full_name"):
            applicant_name = app.form_data["personal"]["full_name"]

        out.append(
            MeritRankItem(
                application_id=app.id,
                reference_id=app.reference_id,
                applicant_name=applicant_name,
                total_score=s.total_score,
                rank=s.rank or 0,
                tie_break_level=s.tie_break_level,
                status=app.status.value if hasattr(app.status, "value") else str(app.status),
                score_breakdown=s.score_breakdown,
            )
        )
    return out


@router.get(
    "/applications/{application_id}",
    response_model=MeritScoreResponse,
    summary="Get detailed merit score and calculation breakdown for an application",
)
def get_application_merit_score(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMMITTEE, UserRole.ADMIN])),
):
    score = (
        db.query(MeritScore)
        .filter(MeritScore.application_id == application_id, MeritScore.is_current == True)
        .first()
    )
    if not score:
        raise EntityNotFoundException("MERIT_SCORE", application_id)
    return score

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import and_, case, cast, Date, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, SelectionResultEnum, UserRole
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.deficiency import Deficiency
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.merit_score import MeritScore
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.selection_result import SelectionResult
from app.models.user import User
from app.schemas.analytics import (
    ApplicationFunnelResponse,
    ApplicationMilestone,
    AuditLogReportItem,
    AuditLogReportResponse,
    OfficerThroughputItem,
    OfficerThroughputResponse,
    SchemeBreakdownsResponse,
    SchemePerformanceSummary,
    SystemOverviewMetrics,
    TimeSeriesPoint,
    VelocityTrendsResponse,
    VerificationDecisionMetrics,
)


def _sanitize_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitizes sensitive security keys and credentials from audit details."""
    if not details:
        return {}
    sensitive_keys = {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "authorization",
    }
    clean = {}
    for k, v in details.items():
        if k.lower() in sensitive_keys:
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = _sanitize_details(v)
        else:
            clean[k] = v
    return clean


class AnalyticsService:
    """
    Read-only, high-performance analytical service for administrative observability,
    reporting, and pipeline monitoring across Phases 0–6.
    Zero mutations, zero commits, zero transactional locks.
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. System Overview Metrics
    # -------------------------------------------------------------------------
    def get_system_overview(
        self,
        scheme_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SystemOverviewMetrics:
        """
        Computes platform-wide state distribution, active quota utilization,
        and high-level pipeline counts.
        """
        app_filters = []
        if scheme_id:
            app_filters.append(Application.scheme_id == scheme_id)
        if start_date:
            app_filters.append(Application.created_at >= start_date)
        if end_date:
            app_filters.append(Application.created_at <= end_date)

        # 1. Current State Distribution (Mutually Exclusive)
        state_query = select(Application.status, func.count(Application.id))
        if app_filters:
            state_query = state_query.where(and_(*app_filters))
        state_query = state_query.group_by(Application.status)

        state_rows = self.db.execute(state_query).all()
        current_state_dist: Dict[str, int] = {s.value: 0 for s in ApplicationStatus}
        total_apps = 0
        for status_val, count_val in state_rows:
            key = status_val.value if hasattr(status_val, "value") else str(status_val)
            current_state_dist[key] = int(count_val)
            total_apps += int(count_val)

        # 2. Active Schemes & Authoritative Quotas
        # Exact source: SchemeVersion.scoring_weights["quota_config"]["total_slots"]
        active_schemes_query = (
            select(SchemeVersion)
            .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
            .where(Scheme.is_active == True, SchemeVersion.is_active == True)
        )
        if scheme_id:
            active_schemes_query = active_schemes_query.where(Scheme.id == scheme_id)
        active_versions = self.db.execute(active_schemes_query).scalars().all()

        active_schemes_count = len({v.scheme_id for v in active_versions})
        total_quota_slots = 0
        for v in active_versions:
            weights = v.scoring_weights or {}
            quota_cfg = weights.get("quota_config") or weights.get("quotas") or {}
            total_quota_slots += int(quota_cfg.get("total_slots", 0))

        # 3. Verified Pool & Selections
        total_selected = current_state_dist.get(ApplicationStatus.SELECTED.value, 0)
        total_waitlisted = current_state_dist.get(ApplicationStatus.WAITLISTED.value, 0)
        total_rejected = current_state_dist.get(ApplicationStatus.REJECTED.value, 0)
        total_verified_pool = current_state_dist.get(ApplicationStatus.VERIFIED.value, 0)

        quota_utilization_rate = (
            round((total_selected / total_quota_slots) * 100.0, 2)
            if total_quota_slots > 0
            else 0.0
        )

        # 4. Deficiencies
        deficiency_query = (
            select(Deficiency.status, func.count(Deficiency.id))
            .group_by(Deficiency.status)
        )
        deficiency_rows = self.db.execute(deficiency_query).all()
        def_map = {str(status): count for status, count in deficiency_rows}
        active_deficiencies = def_map.get("OPEN", 0) + def_map.get("UNDER_REVIEW", 0)
        resolved_deficiencies = def_map.get("RESOLVED", 0)

        # 5. Committee Evaluation Batches
        batch_query = (
            select(
                func.count(CommitteeEvaluationBatch.id),
                func.count(
                    case((CommitteeEvaluationBatch.status == "FINALIZED", 1), else_=None)
                ),
            )
        )
        batch_total, batch_finalized = self.db.execute(batch_query).one()

        # 6. Staff Counts
        staff_query = (
            select(User.role, func.count(User.id))
            .where(User.is_active == True)
            .group_by(User.role)
        )
        staff_rows = self.db.execute(staff_query).all()
        staff_map = {str(r.value if hasattr(r, "value") else r): count for r, count in staff_rows}
        total_officers = staff_map.get(UserRole.OFFICER.value, 0)
        total_committee_members = staff_map.get(UserRole.COMMITTEE.value, 0)

        return SystemOverviewMetrics(
            total_applications=total_apps,
            current_state_distribution=current_state_dist,
            active_schemes_count=active_schemes_count,
            active_schemes_total_quota_slots=total_quota_slots,
            active_schemes_quota_utilization_rate=quota_utilization_rate,
            total_verified_pool=total_verified_pool,
            active_deficiencies_count=active_deficiencies,
            resolved_deficiencies_count=resolved_deficiencies,
            total_evaluation_batches=batch_total or 0,
            finalized_evaluation_batches=batch_finalized or 0,
            total_selected=total_selected,
            total_waitlisted=total_waitlisted,
            total_rejected=total_rejected,
            total_officers=total_officers,
            total_committee_members=total_committee_members,
        )

    # -------------------------------------------------------------------------
    # 2. Cumulative Milestone Funnel
    # -------------------------------------------------------------------------
    def get_application_funnel(
        self, scheme_id: Optional[uuid.UUID] = None
    ) -> ApplicationFunnelResponse:
        """
        Evaluates cumulative sequential progression across lifecycle milestones.
        Source of truth:
          Milestone 1: applications.created_at
          Milestone 2: applications.submitted_at IS NOT NULL
          Milestone 3: audit_logs (new_status='VERIFIED') OR applications.status IN (VERIFIED, MERIT_RANKED, SELECTED, WAITLISTED)
          Milestone 4: merit_scores
          Milestone 5: selection_results (result='SELECTED')
        """
        app_filter = [Application.scheme_id == scheme_id] if scheme_id else []

        # Milestone 1: Drafts Initiated
        m1_query = select(func.count(Application.id))
        if app_filter:
            m1_query = m1_query.where(and_(*app_filter))
        m1_count = self.db.execute(m1_query).scalar() or 0

        # Milestone 2: Applications Submitted
        m2_conditions = [Application.submitted_at.isnot(None)] + app_filter
        m2_query = select(func.count(Application.id)).where(and_(*m2_conditions))
        m2_count = self.db.execute(m2_query).scalar() or 0

        # Milestone 3: Officer Verification Cleared (Historical verified evidence)
        verified_statuses = [
            ApplicationStatus.VERIFIED,
            ApplicationStatus.MERIT_RANKED,
            ApplicationStatus.SELECTED,
            ApplicationStatus.WAITLISTED,
        ]
        audit_subq = (
            select(AuditLog.application_id)
            .where(
                AuditLog.application_id.isnot(None),
                AuditLog.new_status == "VERIFIED",
            )
            .distinct()
        )
        m3_conditions = [
            or_(
                Application.status.in_(verified_statuses),
                Application.id.in_(audit_subq),
            )
        ] + app_filter
        m3_query = select(func.count(distinct(Application.id))).where(and_(*m3_conditions))
        m3_count = self.db.execute(m3_query).scalar() or 0

        # Milestone 4: Merit Ranked
        m4_query = (
            select(func.count(distinct(Application.id)))
            .join(MeritScore, MeritScore.application_id == Application.id)
        )
        if app_filter:
            m4_query = m4_query.where(and_(*app_filter))
        m4_count = self.db.execute(m4_query).scalar() or 0

        # Milestone 5: Award Selected
        m5_conditions = [SelectionResult.result == SelectionResultEnum.SELECTED] + app_filter
        m5_query = (
            select(func.count(distinct(Application.id)))
            .join(SelectionResult, SelectionResult.application_id == Application.id)
            .where(and_(*m5_conditions))
        )
        m5_count = self.db.execute(m5_query).scalar() or 0

        # Guarantee monotonic non-increasing invariant: M1 >= M2 >= M3 >= M4 >= M5
        m2_clamped = min(m2_count, m1_count)
        m3_clamped = min(m3_count, m2_clamped)
        m4_clamped = min(m4_count, m3_clamped)
        m5_clamped = min(m5_count, m4_clamped)

        milestones_def = [
            ("DRAFTS_INITIATED", "Drafts Initiated", m1_count),
            ("SUBMITTED", "Applications Submitted", m2_clamped),
            ("VERIFIED_POOL", "Officer Verification Cleared", m3_clamped),
            ("MERIT_RANKED", "Merit Calculated & Ranked", m4_clamped),
            ("SELECTED", "Award Selected", m5_clamped),
        ]

        milestone_items: List[ApplicationMilestone] = []
        prev_count = m1_count
        for key, label, count in milestones_def:
            from_start = round((count / m1_count * 100.0), 2) if m1_count > 0 else 0.0
            from_prev = round((count / prev_count * 100.0), 2) if prev_count > 0 else 0.0
            milestone_items.append(
                ApplicationMilestone(
                    milestone_key=key,
                    milestone_label=label,
                    count=count,
                    conversion_from_start_rate=from_start,
                    conversion_from_previous_rate=from_prev,
                )
            )
            prev_count = count

        return ApplicationFunnelResponse(
            total_initiated=m1_count,
            milestones=milestone_items,
        )

    # -------------------------------------------------------------------------
    # 3. Intake & Velocity Trends
    # -------------------------------------------------------------------------
    def get_velocity_trends(
        self,
        scheme_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> VelocityTrendsResponse:
        """
        Time-series aggregations for daily submission, verification, and selection velocity.
        """
        sub_filters = [Application.submitted_at.isnot(None)]
        if scheme_id:
            sub_filters.append(Application.scheme_id == scheme_id)
        if start_date:
            sub_filters.append(Application.submitted_at >= start_date)
        if end_date:
            sub_filters.append(Application.submitted_at <= end_date)

        sub_query = (
            select(
                cast(Application.submitted_at, Date).label("d"),
                func.count(Application.id).label("cnt"),
            )
            .where(and_(*sub_filters))
            .group_by(cast(Application.submitted_at, Date))
            .order_by("d")
        )
        sub_rows = self.db.execute(sub_query).all()

        ver_filters = [Application.scrutiny_completed_at.isnot(None)]
        if scheme_id:
            ver_filters.append(Application.scheme_id == scheme_id)
        if start_date:
            ver_filters.append(Application.scrutiny_completed_at >= start_date)
        if end_date:
            ver_filters.append(Application.scrutiny_completed_at <= end_date)

        ver_query = (
            select(
                cast(Application.scrutiny_completed_at, Date).label("d"),
                func.count(Application.id).label("cnt"),
            )
            .where(and_(*ver_filters))
            .group_by(cast(Application.scrutiny_completed_at, Date))
            .order_by("d")
        )
        ver_rows = self.db.execute(ver_query).all()

        sel_filters = [SelectionResult.finalized_at.isnot(None)]
        if scheme_id:
            sel_filters.append(Application.scheme_id == scheme_id)
        if start_date:
            sel_filters.append(SelectionResult.finalized_at >= start_date)
        if end_date:
            sel_filters.append(SelectionResult.finalized_at <= end_date)

        sel_query = (
            select(
                cast(SelectionResult.finalized_at, Date).label("d"),
                func.count(SelectionResult.id).label("cnt"),
            )
            .join(Application, Application.id == SelectionResult.application_id)
            .where(and_(*sel_filters))
            .group_by(cast(SelectionResult.finalized_at, Date))
            .order_by("d")
        )
        sel_rows = self.db.execute(sel_query).all()

        date_map: Dict[str, Dict[str, int]] = {}
        for d_val, cnt in sub_rows:
            d_str = str(d_val)
            date_map.setdefault(d_str, {"sub": 0, "ver": 0, "sel": 0})["sub"] = int(cnt)
        for d_val, cnt in ver_rows:
            d_str = str(d_val)
            date_map.setdefault(d_str, {"sub": 0, "ver": 0, "sel": 0})["ver"] = int(cnt)
        for d_val, cnt in sel_rows:
            d_str = str(d_val)
            date_map.setdefault(d_str, {"sub": 0, "ver": 0, "sel": 0})["sel"] = int(cnt)

        points = [
            TimeSeriesPoint(
                date=d_str,
                submissions_count=vals["sub"],
                verifications_count=vals["ver"],
                selections_count=vals["sel"],
            )
            for d_str, vals in sorted(date_map.items())
        ]

        return VelocityTrendsResponse(
            start_date=start_date.isoformat() if start_date else "",
            end_date=end_date.isoformat() if end_date else "",
            granularity=granularity,
            data_points=points,
        )

    # -------------------------------------------------------------------------
    # 4. Scheme & Version-Bound Performance
    # -------------------------------------------------------------------------
    def get_scheme_breakdowns(
        self, scheme_id: Optional[uuid.UUID] = None
    ) -> SchemeBreakdownsResponse:
        """
        Computes scheme and version performance strictly bound to SchemeVersion.scoring_weights.
        """
        versions_query = (
            select(SchemeVersion, Scheme)
            .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
            .where(SchemeVersion.is_active == True)
        )
        if scheme_id:
            versions_query = versions_query.where(Scheme.id == scheme_id)

        rows = self.db.execute(versions_query).all()
        summaries: List[SchemePerformanceSummary] = []

        for sv, sc in rows:
            weights = sv.scoring_weights or {}
            quota_cfg = weights.get("quota_config") or weights.get("quotas") or {}
            quota_slots = int(quota_cfg.get("total_slots", 0))

            apps_query = (
                select(Application.status, func.count(Application.id))
                .where(Application.scheme_version_id == sv.id)
                .group_by(Application.status)
            )
            app_counts = dict(self.db.execute(apps_query).all())
            total_apps = sum(app_counts.values())

            if total_apps == 0:
                apps_query_fallback = (
                    select(Application.status, func.count(Application.id))
                    .where(Application.scheme_id == sc.id)
                    .group_by(Application.status)
                )
                app_counts = dict(self.db.execute(apps_query_fallback).all())
                total_apps = sum(app_counts.values())

            selected_cnt = app_counts.get(ApplicationStatus.SELECTED, 0)
            waitlisted_cnt = app_counts.get(ApplicationStatus.WAITLISTED, 0)
            rejected_cnt = app_counts.get(ApplicationStatus.REJECTED, 0)
            verified_cnt = (
                app_counts.get(ApplicationStatus.VERIFIED, 0)
                + app_counts.get(ApplicationStatus.MERIT_RANKED, 0)
                + selected_cnt
                + waitlisted_cnt
            )

            exhaustion_rate = (
                round((selected_cnt / quota_slots * 100.0), 2)
                if quota_slots > 0
                else 0.0
            )

            summaries.append(
                SchemePerformanceSummary(
                    scheme_id=sc.id,
                    scheme_code=sc.scheme_code,
                    scheme_name=sc.name,
                    scheme_version_id=sv.id,
                    scheme_version=sv.scheme_version,
                    is_active=sc.is_active and sv.is_active,
                    quota_slots=quota_slots,
                    total_applications=total_apps,
                    verified_count=verified_cnt,
                    selected_count=selected_cnt,
                    waitlisted_count=waitlisted_cnt,
                    rejected_count=rejected_cnt,
                    quota_exhaustion_rate=exhaustion_rate,
                )
            )

        return SchemeBreakdownsResponse(schemes=summaries)

    # -------------------------------------------------------------------------
    # 5. Staff Verification Throughput & Velocity
    # -------------------------------------------------------------------------
    def get_officer_throughput(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> OfficerThroughputResponse:
        """
        Measures individual officer workload and throughput.
        Officer display name is exposed; email and applicant PII are strictly excluded.
        Metric honestly labeled as average document-to-verification duration (hours).
        """
        officers_query = select(User).where(
            User.role == UserRole.OFFICER, User.is_active == True
        )
        officers = self.db.execute(officers_query).scalars().all()
        items: List[OfficerThroughputItem] = []

        for off in officers:
            apps_scrutinized = (
                self.db.execute(
                    select(func.count(Application.id)).where(
                        Application.scrutiny_officer_id == off.id
                    )
                ).scalar()
                or 0
            )

            apps_verified = (
                self.db.execute(
                    select(func.count(Application.id)).where(
                        Application.scrutiny_officer_id == off.id,
                        Application.status.in_(
                            [
                                ApplicationStatus.VERIFIED,
                                ApplicationStatus.MERIT_RANKED,
                                ApplicationStatus.SELECTED,
                                ApplicationStatus.WAITLISTED,
                            ]
                        ),
                    )
                ).scalar()
                or 0
            )

            deficiencies_flagged = (
                self.db.execute(
                    select(func.count(AuditLog.id)).where(
                        AuditLog.actor_id == off.id,
                        AuditLog.action.in_(
                            ["APPLICATION_MARKED_DEFICIENT", "DEFICIENCY_FLAGGED"]
                        ),
                    )
                ).scalar()
                or 0
            )

            overrides_count = (
                self.db.execute(
                    select(func.count(DocumentVerification.id)).where(
                        DocumentVerification.verified_by == off.id,
                        DocumentVerification.ai_override == True,
                    )
                ).scalar()
                or 0
            )

            duration_query = select(
                DocumentVerification.created_at,
                DocumentVerification.verified_at,
            ).where(
                DocumentVerification.verified_by == off.id,
                DocumentVerification.verified_at.isnot(None),
                DocumentVerification.created_at.isnot(None),
            )
            duration_rows = self.db.execute(duration_query).all()

            total_hours = 0.0
            count_measured = 0
            for c_at, v_at in duration_rows:
                if v_at and c_at and v_at >= c_at:
                    total_hours += (v_at - c_at).total_seconds() / 3600.0
                    count_measured += 1

            avg_hours = (
                round(total_hours / count_measured, 2) if count_measured > 0 else 0.0
            )

            items.append(
                OfficerThroughputItem(
                    officer_id=off.id,
                    officer_name=off.full_name,
                    assigned_applications_count=apps_scrutinized,
                    verified_count=apps_verified,
                    deficiencies_flagged_count=deficiencies_flagged,
                    human_overrides_count=overrides_count,
                    avg_verification_duration_hours=avg_hours,
                )
            )

        return OfficerThroughputResponse(officers=items)

    # -------------------------------------------------------------------------
    # 6. Verification Decision Integrity & AI-Human Agreement
    # -------------------------------------------------------------------------
    def get_decision_metrics(
        self,
        scheme_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> VerificationDecisionMetrics:
        """
        Computes AI-human agreement and override rates from existing document_verifications.
        Evaluated Population N_eval:
          officer_decision IS NOT NULL and verification_status IN ('VERIFIED', 'FLAGGED')
        Agreement: ai_override == False
        Override: ai_override == True
        """
        filters = [
            DocumentVerification.officer_decision.isnot(None),
            DocumentVerification.verification_status.in_(["VERIFIED", "FLAGGED"]),
        ]
        if start_date:
            filters.append(DocumentVerification.verified_at >= start_date)
        if end_date:
            filters.append(DocumentVerification.verified_at <= end_date)

        query = (
            select(
                DocumentVerification.verification_status,
                DocumentVerification.officer_decision,
                DocumentVerification.ai_override,
            )
            .join(Document, Document.id == DocumentVerification.document_id)
            .join(Application, Application.id == Document.application_id)
        )
        if scheme_id:
            filters.append(Application.scheme_id == scheme_id)

        query = query.where(and_(*filters))
        records = self.db.execute(query).all()

        n_eval = len(records)
        agreements = 0
        overrides = 0
        ai_flagged_human_ver = 0
        ai_ver_human_rej = 0

        for ai_stat, human_dec, is_override in records:
            ai_upper = str(ai_stat).upper()
            human_upper = str(human_dec).upper()

            if is_override:
                overrides += 1
                if ai_upper == "FLAGGED" and human_upper == "VERIFIED":
                    ai_flagged_human_ver += 1
                elif ai_upper == "VERIFIED" and human_upper == "REJECTED":
                    ai_ver_human_rej += 1
            else:
                agreements += 1

        r_agree = round((agreements / n_eval * 100.0), 2) if n_eval > 0 else 100.0
        r_override = round((overrides / n_eval * 100.0), 2) if n_eval > 0 else 0.0

        return VerificationDecisionMetrics(
            total_documents_evaluated=n_eval,
            ai_human_agreements=agreements,
            human_overrides=overrides,
            ai_human_agreement_rate=r_agree,
            human_override_rate=r_override,
            override_breakdown={
                "AI_FLAGGED_HUMAN_VERIFIED": ai_flagged_human_ver,
                "AI_VERIFIED_HUMAN_REJECTED": ai_ver_human_rej,
            },
        )

    # -------------------------------------------------------------------------
    # 7. Searchable System Audit Logs
    # -------------------------------------------------------------------------
    def get_audit_logs_report(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        application_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
    ) -> AuditLogReportResponse:
        """
        Searchable, indexed paginated audit trail. Sensitive fields are scrubbed.
        """
        filters = []
        if action:
            filters.append(AuditLog.action == action)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if actor_id:
            filters.append(AuditLog.actor_id == actor_id)
        if application_id:
            filters.append(AuditLog.application_id == application_id)
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        if end_date:
            filters.append(AuditLog.created_at <= end_date)

        count_query = select(func.count(AuditLog.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total_count = self.db.execute(count_query).scalar() or 0

        offset = (max(page, 1) - 1) * min(limit, 100)
        logs_query = (
            select(AuditLog, User.full_name)
            .outerjoin(User, User.id == AuditLog.actor_id)
        )
        if filters:
            logs_query = logs_query.where(and_(*filters))
        logs_query = logs_query.order_by(AuditLog.created_at.desc()).offset(offset).limit(min(limit, 100))
        rows = self.db.execute(logs_query).all()

        items: List[AuditLogReportItem] = []
        for log_entry, full_name in rows:
            actor_name = full_name or "SYSTEM"
            items.append(
                AuditLogReportItem(
                    id=log_entry.id,
                    created_at=log_entry.created_at,
                    actor_id=log_entry.actor_id,
                    actor_name=actor_name,
                    entity_type=log_entry.entity_type,
                    entity_id=log_entry.entity_id,
                    action=log_entry.action,
                    previous_status=log_entry.previous_status,
                    new_status=log_entry.new_status,
                    details=_sanitize_details(log_entry.details),
                )
            )

        return AuditLogReportResponse(
            total_count=total_count,
            page=page,
            limit=limit,
            logs=items,
        )

    # -------------------------------------------------------------------------
    # 8. Streaming CSV Exports (Server-side 10,000-row cap)
    # -------------------------------------------------------------------------
    def export_applications_stream(
        self,
        scheme_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 10000,
    ) -> Generator[str, None, None]:
        """
        Streaming CSV export of applications.
        Server-side cap: strictly min(limit, 10000).
        Applicant PII (names, emails, phones, Aadhaar, account numbers) is strictly excluded.
        """
        actual_limit = min(max(int(limit or 10000), 1), 10000)

        filters = []
        if scheme_id:
            filters.append(Application.scheme_id == scheme_id)
        if status:
            filters.append(Application.status == status)
        if start_date:
            filters.append(Application.created_at >= start_date)
        if end_date:
            filters.append(Application.created_at <= end_date)

        query = (
            select(
                Application.reference_id,
                Scheme.scheme_code.label("scheme_code"),
                SchemeVersion.scheme_version.label("scheme_version"),
                Application.status,
                Application.submitted_at,
                Application.scrutiny_completed_at,
                SelectionResult.result.label("selection_result"),
                SelectionResult.rank.label("selection_rank"),
                SelectionResult.selection_round,
                SelectionResult.is_override,
            )
            .join(Scheme, Scheme.id == Application.scheme_id)
            .outerjoin(SchemeVersion, SchemeVersion.id == Application.scheme_version_id)
            .outerjoin(SelectionResult, SelectionResult.application_id == Application.id)
        )
        if filters:
            query = query.where(and_(*filters))
        query = query.order_by(Application.created_at.desc()).limit(actual_limit)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "reference_id",
                "scheme_code",
                "scheme_version",
                "status",
                "submitted_at",
                "scrutiny_completed_at",
                "selection_result",
                "merit_rank",
                "selection_round",
                "is_override",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        rows = self.db.execute(query).all()
        for r in rows:
            writer.writerow(
                [
                    r.reference_id,
                    r.scheme_code,
                    r.scheme_version or "1.0",
                    str(r.status.value if hasattr(r.status, "value") else r.status),
                    r.submitted_at.isoformat() if r.submitted_at else "",
                    r.scrutiny_completed_at.isoformat() if r.scrutiny_completed_at else "",
                    str(r.selection_result.value if hasattr(r.selection_result, "value") else (r.selection_result or "")),
                    r.selection_rank if r.selection_rank is not None else "",
                    r.selection_round if r.selection_round is not None else "",
                    "TRUE" if r.is_override else "FALSE",
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    def export_audit_logs_stream(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 10000,
    ) -> Generator[str, None, None]:
        """
        Streaming CSV export of audit logs.
        Server-side cap: strictly min(limit, 10000).
        Credentials and secrets are scrubbed from details.
        """
        actual_limit = min(max(int(limit or 10000), 1), 10000)

        filters = []
        if action:
            filters.append(AuditLog.action == action)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        if end_date:
            filters.append(AuditLog.created_at <= end_date)

        query = select(AuditLog)
        if filters:
            query = query.where(and_(*filters))
        query = query.order_by(AuditLog.created_at.desc()).limit(actual_limit)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "id",
                "created_at",
                "actor_id",
                "entity_type",
                "entity_id",
                "action",
                "previous_status",
                "new_status",
                "details_summary",
            ]
        )
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        rows = self.db.execute(query).scalars().all()
        for log_entry in rows:
            clean_details = _sanitize_details(log_entry.details)
            details_str = json.dumps(clean_details)
            writer.writerow(
                [
                    str(log_entry.id),
                    log_entry.created_at.isoformat(),
                    str(log_entry.actor_id or ""),
                    log_entry.entity_type,
                    log_entry.entity_id,
                    log_entry.action,
                    log_entry.previous_status or "",
                    log_entry.new_status or "",
                    details_str,
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

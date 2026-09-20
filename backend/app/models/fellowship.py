import uuid
from datetime import datetime, date
from typing import Any, Dict
from sqlalchemy import String, Integer, Float, Text, Date, DateTime, Enum, ForeignKey, Numeric, Boolean, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import DisbursementStatus, SubmissionStatus, FellowshipStatus


class FellowshipRecord(Base):
    __tablename__ = "fellowship_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    fellowship_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sanction_order_number: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    sanction_mode: Mapped[str] = mapped_column(String(32), default="DEMO_SIMULATED", nullable=False)
    sanction_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheme_versions.id", ondelete="RESTRICT"), nullable=False
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_officer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), default=FellowshipStatus.ACTIVE.value, nullable=False)
    current_year: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tenure_years: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guide_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    research_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    award_letter_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    disbursement_status: Mapped[DisbursementStatus] = mapped_column(
        Enum(DisbursementStatus, native_enum=False),
        default=DisbursementStatus.SCHEDULED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="fellowship_records")
    scheme = relationship("Scheme")
    scheme_version = relationship("SchemeVersion")
    applicant = relationship("User", foreign_keys=[applicant_id])
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    renewals = relationship("RenewalSubmission", back_populates="fellowship")
    progress_reports = relationship("ProgressReport", back_populates="fellowship")
    installments = relationship("DisbursementInstallment", back_populates="fellowship")


class RenewalSubmission(Base):
    __tablename__ = "renewal_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fellowship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fellowship_records.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    renewal_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False),
        default=SubmissionStatus.PENDING,
        nullable=False,
    )
    annual_progress_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    marks_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    continuation_certificate_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    marksheet_document_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    documents: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewer_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    deficiency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deficiencies.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    fellowship = relationship("FellowshipRecord", back_populates="renewals")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    deficiency = relationship("Deficiency", foreign_keys=[deficiency_id])


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fellowship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fellowship_records.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    report_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publications_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    presentations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    patents_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supervisor_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    supervisor_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False),
        default=SubmissionStatus.PENDING,
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewer_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    deficiency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deficiencies.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    fellowship = relationship("FellowshipRecord", back_populates="progress_reports")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    deficiency = relationship("Deficiency", foreign_keys=[deficiency_id])


class DisbursementInstallment(Base):
    __tablename__ = "disbursement_installments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fellowship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fellowship_records.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    stipend_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    contingency_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    hra_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(32), default=DisbursementStatus.SCHEDULED.value, nullable=False, index=True
    )
    integration_mode: Mapped[str] = mapped_column(String(32), default="SIMULATED_MOCK", nullable=False)
    payment_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )
    pfms_reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_reference_utr: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    account_number_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(16), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    fellowship = relationship("FellowshipRecord", back_populates="installments")
    approver = relationship("User", foreign_keys=[approved_by])

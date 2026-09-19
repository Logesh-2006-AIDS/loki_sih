import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Integer, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import DisbursementStatus, SubmissionStatus


class FellowshipRecord(Base):
    __tablename__ = "fellowship_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    current_year: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    disbursement_status: Mapped[DisbursementStatus] = mapped_column(
        Enum(DisbursementStatus, native_enum=False),
        default=DisbursementStatus.PENDING,
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
    renewals = relationship("RenewalSubmission", back_populates="fellowship", cascade="all, delete-orphan")
    progress_reports = relationship("ProgressReport", back_populates="fellowship", cascade="all, delete-orphan")


class RenewalSubmission(Base):
    __tablename__ = "renewal_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fellowship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fellowship_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False),
        default=SubmissionStatus.PENDING,
        nullable=False,
    )
    documents: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    fellowship = relationship("FellowshipRecord", back_populates="renewals")


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fellowship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fellowship_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False),
        default=SubmissionStatus.PENDING,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    fellowship = relationship("FellowshipRecord", back_populates="progress_reports")

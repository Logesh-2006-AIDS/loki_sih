import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Float, DateTime, Enum, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheme_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    form_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    frozen_rules_snapshot: Mapped[Dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    merit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    applicant = relationship("User", back_populates="applications")
    scheme = relationship("Scheme", back_populates="applications")
    scheme_version = relationship("SchemeVersion", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    deficiencies = relationship("Deficiency", back_populates="application", cascade="all, delete-orphan")
    merit_scores = relationship("MeritScore", back_populates="application", cascade="all, delete-orphan")
    selection_results = relationship("SelectionResult", back_populates="application", cascade="all, delete-orphan")
    fellowship_records = relationship("FellowshipRecord", back_populates="application", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="application")

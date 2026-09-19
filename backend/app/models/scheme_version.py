import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class SchemeVersion(Base):
    """
    Authoritative configuration entity for a scheme version.
    Contains the exact eligibility rules, form schema, required documents,
    and scoring weights for a specific version of a scheme.
    """
    __tablename__ = "scheme_versions"
    __table_args__ = (
        UniqueConstraint("scheme_code", "scheme_version", name="uq_scheme_code_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_code: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    scheme_version: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explicit DEMO / PROTOTYPE notice indicator
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Authoritative scheme configuration
    eligibility_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    form_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    required_documents: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    scoring_weights: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    scheme = relationship("Scheme", back_populates="versions")
    applications = relationship("Application", back_populates="scheme_version")

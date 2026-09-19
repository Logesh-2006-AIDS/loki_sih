import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Boolean, Text, DateTime, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Architectural readiness for future historical scheme version management
    scheme_version: Mapped[str] = mapped_column(
        String(32), default="1.0", nullable=False
    )
    # Explicit DEMO / PROTOTYPE notice indicator
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    applications = relationship("Application", back_populates="scheme", cascade="all, delete-orphan")
    officer_assignments = relationship("OfficerAssignment", back_populates="scheme", cascade="all, delete-orphan")

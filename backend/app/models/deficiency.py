import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Deficiency(Base):
    __tablename__ = "deficiencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cycle: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    replacement_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    applicant_message: Mapped[str] = mapped_column(Text, nullable=False)
    applicant_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    notification_dispatched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    replacement_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("Application", back_populates="deficiencies")
    document = relationship("Document", back_populates="deficiencies", foreign_keys=[document_id])
    replacement_document = relationship(
        "Document", back_populates="replacement_deficiencies", foreign_keys=[replacement_document_id]
    )

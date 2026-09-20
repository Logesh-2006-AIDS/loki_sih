import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import DocumentStatus


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Phase 5 Lineage and Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="documents")
    verifications = relationship("DocumentVerification", back_populates="document", cascade="all, delete-orphan")
    deficiencies = relationship("Deficiency", back_populates="document", foreign_keys="[Deficiency.document_id]")
    replacement_deficiencies = relationship(
        "Deficiency", back_populates="replacement_document", foreign_keys="[Deficiency.replacement_document_id]"
    )
    parent_document = relationship("Document", remote_side=[id], foreign_keys=[parent_document_id])
    superseded_by = relationship("Document", remote_side=[id], foreign_keys=[superseded_by_id])

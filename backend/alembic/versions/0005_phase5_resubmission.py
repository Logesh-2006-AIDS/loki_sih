"""phase 5 deficiency and resubmission

Revision ID: 0005_phase5_deficiency_resubmission
Revises: 0004_phase4_officer_scrutiny
Create Date: 2026-09-20 08:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_phase5_resubmission"
down_revision: Union[str, None] = "0004_phase4_officer_scrutiny"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add versioning and lineage columns to documents
    op.add_column(
        "documents",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column(
            "parent_document_id",
            sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "superseded_by_id",
            sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_documents_is_current",
        "documents",
        ["is_current"],
        unique=False,
    )
    op.create_index(
        "ix_documents_app_type_current",
        "documents",
        ["application_id", "document_type", "is_current"],
        unique=False,
    )

    # 2. Add cycle, replacement linkage, and notification tracking to deficiencies
    op.add_column(
        "deficiencies",
        sa.Column("cycle", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "deficiencies",
        sa.Column(
            "replacement_document_id",
            sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "deficiencies",
        sa.Column("applicant_remarks", sa.Text(), nullable=True),
    )
    op.add_column(
        "deficiencies",
        sa.Column("replacement_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "deficiencies",
        sa.Column("notification_dispatched", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "deficiencies",
        sa.Column("notification_dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_deficiencies_app_cycle",
        "deficiencies",
        ["application_id", "cycle"],
        unique=False,
    )
    op.create_index(
        "ix_deficiencies_replacement_doc_id",
        "deficiencies",
        ["replacement_document_id"],
        unique=False,
    )

    # 3. Add resubmission tracking columns to applications
    op.add_column(
        "applications",
        sa.Column("resubmission_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "applications",
        sa.Column("resubmitted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # 3. Revert applications columns
    op.drop_column("applications", "resubmitted_at")
    op.drop_column("applications", "resubmission_count")

    # 2. Revert deficiencies columns
    op.drop_index("ix_deficiencies_replacement_doc_id", table_name="deficiencies")
    op.drop_index("ix_deficiencies_app_cycle", table_name="deficiencies")
    op.drop_column("deficiencies", "notification_dispatched_at")
    op.drop_column("deficiencies", "notification_dispatched")
    op.drop_column("deficiencies", "replacement_uploaded_at")
    op.drop_column("deficiencies", "applicant_remarks")
    op.drop_column("deficiencies", "replacement_document_id")
    op.drop_column("deficiencies", "cycle")

    # 1. Revert documents columns
    op.drop_index("ix_documents_app_type_current", table_name="documents")
    op.drop_index("ix_documents_is_current", table_name="documents")
    op.drop_column("documents", "superseded_by_id")
    op.drop_column("documents", "parent_document_id")
    op.drop_column("documents", "is_current")
    op.drop_column("documents", "version")

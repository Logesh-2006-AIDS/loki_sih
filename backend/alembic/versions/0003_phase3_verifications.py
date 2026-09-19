"""phase 3 document verifications

Revision ID: 0003_phase3_verifications
Revises: 0002_phase1_scheme_versions
Create Date: 2026-09-19 15:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase3_verifications"
down_revision: Union[str, None] = "0002_phase1_scheme_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add single authoritative Phase 3 columns to document_verifications
    op.add_column(
        "document_verifications",
        sa.Column("ocr_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_verifications",
        sa.Column(
            "extracted_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "document_verifications",
        sa.Column(
            "field_confidences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "document_verifications",
        sa.Column(
            "comparison_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "document_verifications",
        sa.Column("overall_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "document_verifications",
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "document_verifications",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Make legacy columns nullable so they don't block inserts
    op.alter_column("document_verifications", "extracted_data", nullable=True)
    op.alter_column("document_verifications", "matched_fields", nullable=True)
    op.alter_column("document_verifications", "mismatched_fields", nullable=True)


def downgrade() -> None:
    op.alter_column("document_verifications", "mismatched_fields", nullable=False)
    op.alter_column("document_verifications", "matched_fields", nullable=False)
    op.alter_column("document_verifications", "extracted_data", nullable=False)

    op.drop_column("document_verifications", "processed_at")
    op.drop_column("document_verifications", "flags")
    op.drop_column("document_verifications", "overall_confidence")
    op.drop_column("document_verifications", "comparison_results")
    op.drop_column("document_verifications", "field_confidences")
    op.drop_column("document_verifications", "extracted_fields")
    op.drop_column("document_verifications", "ocr_text")

"""phase 1 scheme versions

Revision ID: 0002_phase1_scheme_versions
Revises: 0001_initial_phase0_tables
Create Date: 2026-09-19 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase1_scheme_versions"
down_revision: Union[str, None] = "0001_initial_phase0_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create scheme_versions table
    op.create_table(
        "scheme_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scheme_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheme_code", sa.String(length=64), nullable=False),
        sa.Column("scheme_version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "eligibility_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "form_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "required_documents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "scoring_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_scheme_versions_scheme_id", "scheme_versions", ["scheme_id"]
    )
    op.create_index(
        "ix_scheme_versions_scheme_code", "scheme_versions", ["scheme_code"]
    )
    op.create_unique_constraint(
        "uq_scheme_code_version", "scheme_versions", ["scheme_code", "scheme_version"]
    )

    # 2. Add scheme_version_id and frozen_rules_snapshot to applications table
    op.add_column(
        "applications",
        sa.Column(
            "scheme_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scheme_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "applications",
        sa.Column(
            "frozen_rules_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_applications_scheme_version_id", "applications", ["scheme_version_id"]
    )

    # 3. Backfill initial version 1.0 from existing schemes table
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO scheme_versions (
                id, scheme_id, scheme_code, scheme_version, name, description,
                is_demo, eligibility_rules, form_schema, required_documents, scoring_weights,
                is_active, is_locked, created_at, updated_at
            )
            SELECT 
                gen_random_uuid(), id, scheme_code, scheme_version, name, description,
                is_demo, eligibility_rules, form_schema, required_documents, scoring_weights,
                is_active, false, created_at, updated_at
            FROM schemes
            ON CONFLICT (scheme_code, scheme_version) DO NOTHING;
            """
        )
    )

    # 4. Bind existing applications to their scheme's version 1.0
    conn.execute(
        sa.text(
            """
            UPDATE applications a
            SET scheme_version_id = sv.id,
                frozen_rules_snapshot = sv.eligibility_rules
            FROM scheme_versions sv
            WHERE sv.scheme_id = a.scheme_id
              AND a.scheme_version_id IS NULL;
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_applications_scheme_version_id", table_name="applications")
    op.drop_column("applications", "frozen_rules_snapshot")
    op.drop_column("applications", "scheme_version_id")
    op.drop_constraint("uq_scheme_code_version", "scheme_versions", type_="unique")
    op.drop_index("ix_scheme_versions_scheme_code", table_name="scheme_versions")
    op.drop_index("ix_scheme_versions_scheme_id", table_name="scheme_versions")
    op.drop_table("scheme_versions")

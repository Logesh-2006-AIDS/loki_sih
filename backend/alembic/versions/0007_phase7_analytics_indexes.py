"""phase 7 analytics composite indexes

Revision ID: 0007_phase7_analytics_indexes
Revises: 0006_phase6_merit_committee
Create Date: 2026-09-20 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007_phase7_analytics_indexes"
down_revision: Union[str, None] = "0006_phase6_merit_committee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Applications scheme + status + created_at composite index
    op.create_index(
        "ix_applications_scheme_status_created",
        "applications",
        ["scheme_id", "status", "created_at"],
        unique=False,
    )

    # 2. Applications submitted_at intake trend index
    op.create_index(
        "ix_applications_submitted_at",
        "applications",
        ["submitted_at"],
        unique=False,
    )

    # 3. Audit logs action + created_at composite index
    op.create_index(
        "ix_audit_logs_action_created_at",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )

    # 4. Audit logs actor_id + created_at composite index
    op.create_index(
        "ix_audit_logs_actor_created_at",
        "audit_logs",
        ["actor_id", "created_at"],
        unique=False,
    )

    # 5. Audit logs entity_type + entity_id + created_at composite index
    op.create_index(
        "ix_audit_logs_entity_created_at",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )

    # 6. Deficiencies status + created_at composite index
    op.create_index(
        "ix_deficiencies_status_created_at",
        "deficiencies",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deficiencies_status_created_at", table_name="deficiencies")
    op.drop_index("ix_audit_logs_entity_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action_created_at", table_name="audit_logs")
    op.drop_index("ix_applications_submitted_at", table_name="applications")
    op.drop_index("ix_applications_scheme_status_created", table_name="applications")

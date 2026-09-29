"""staff registration requests and user account status

Revision ID: 0009_staff_registration_requests
Revises: 0008_phase8_fellowships
Create Date: 2026-09-28 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0009_staff_registration_requests"
down_revision: Union[str, None] = "0008_phase8_fellowships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add account_status column to users table
    op.add_column(
        "users",
        sa.Column(
            "account_status",
            sa.String(length=32),
            server_default="ACTIVE",
            nullable=False,
        ),
    )

    # 2. Create staff_registration_requests table
    op.create_table(
        "staff_registration_requests",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("requested_role", sa.String(length=32), nullable=False),
        sa.Column("employee_id", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_staff_registration_requests_user_id",
        "staff_registration_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_staff_registration_requests_status",
        "staff_registration_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_registration_requests_status",
        table_name="staff_registration_requests",
    )
    op.drop_index(
        "ix_staff_registration_requests_user_id",
        table_name="staff_registration_requests",
    )
    op.drop_table("staff_registration_requests")
    op.drop_column("users", "account_status")

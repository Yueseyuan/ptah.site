"""Add organizations table, organization_id to users, and inquiries table

Revision ID: 003
Revises: 5efe1b9e82b5
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "5efe1b9e82b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"], unique=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True))

    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("credit_reports.id"), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("inquiry_type", sa.String(), nullable=True, server_default="hard"),
        sa.Column("subscriber_name", sa.String(), nullable=True),
        sa.Column("inquiry_date", sa.String(), nullable=True),
        sa.Column("purpose", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inquiries_id", "inquiries", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("inquiries")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("organization_id")
    op.drop_table("organizations")

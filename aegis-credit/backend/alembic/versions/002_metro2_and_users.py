"""Add Metro 2 fields, metro2_findings, users, and audit_logs tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Metro 2 columns to tradelines
    op.add_column("tradelines", sa.Column("high_balance", sa.Float(), nullable=True))
    op.add_column("tradelines", sa.Column("past_due_amount", sa.Float(), nullable=True))
    op.add_column("tradelines", sa.Column("scheduled_payment_amount", sa.Float(), nullable=True))
    op.add_column("tradelines", sa.Column("payment_rating", sa.String(), nullable=True))
    op.add_column("tradelines", sa.Column("compliance_condition_code", sa.String(), nullable=True))
    op.add_column("tradelines", sa.Column("consumer_information_indicator", sa.String(), nullable=True))
    op.add_column("tradelines", sa.Column("dofd", sa.String(), nullable=True))
    op.add_column("tradelines", sa.Column("date_reported", sa.String(), nullable=True))
    op.add_column("tradelines", sa.Column("remarks", sa.Text(), nullable=True))
    op.add_column("tradelines", sa.Column("raw_source_text", sa.Text(), nullable=True))

    # Create metro2_findings table
    op.create_table(
        "metro2_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("tradeline_id", sa.Integer(), sa.ForeignKey("tradelines.id"), nullable=True),
        sa.Column("rule_code", sa.String(), nullable=True),
        sa.Column("rule_name", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("fcra_section", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metro2_findings_id", "metro2_findings", ["id"])

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("metro2_findings")
    op.drop_column("tradelines", "raw_source_text")
    op.drop_column("tradelines", "remarks")
    op.drop_column("tradelines", "date_reported")
    op.drop_column("tradelines", "dofd")
    op.drop_column("tradelines", "consumer_information_indicator")
    op.drop_column("tradelines", "compliance_condition_code")
    op.drop_column("tradelines", "payment_rating")
    op.drop_column("tradelines", "scheduled_payment_amount")
    op.drop_column("tradelines", "past_due_amount")
    op.drop_column("tradelines", "high_balance")

"""Add personal_info, federal_laws, agency_guidance, state_laws, case_law tables

Revision ID: 004
Revises: 003
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # personal_info table
    op.create_table(
        "personal_info",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("credit_reports.id"), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("current_name", sa.String(), nullable=True),
        sa.Column("aliases", sa.Text(), nullable=True),
        sa.Column("current_address", sa.String(), nullable=True),
        sa.Column("previous_addresses", sa.Text(), nullable=True),
        sa.Column("current_employer", sa.String(), nullable=True),
        sa.Column("previous_employers", sa.Text(), nullable=True),
        sa.Column("phone_numbers", sa.Text(), nullable=True),
        sa.Column("dob", sa.String(), nullable=True),
        sa.Column("ssn_last4", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_info_id", "personal_info", ["id"], unique=False)

    # federal_laws table
    op.create_table(
        "federal_laws",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("short_name", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("citation", sa.String(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_federal_laws_id", "federal_laws", ["id"], unique=False)

    # agency_guidance table
    op.create_table(
        "agency_guidance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agency", sa.String(), nullable=True),
        sa.Column("document_name", sa.String(), nullable=True),
        sa.Column("publication_date", sa.String(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agency_guidance_id", "agency_guidance", ["id"], unique=False)

    # state_laws table
    op.create_table(
        "state_laws",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("statute", sa.String(), nullable=True),
        sa.Column("citation", sa.String(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("effective_date", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_laws_id", "state_laws", ["id"], unique=False)

    # case_law table
    op.create_table(
        "case_law",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_name", sa.String(), nullable=True),
        sa.Column("citation", sa.String(), nullable=True),
        sa.Column("court", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("holding_summary", sa.Text(), nullable=True),
        sa.Column("legal_principle", sa.Text(), nullable=True),
        sa.Column("relevance_tags", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_law_id", "case_law", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("case_law")
    op.drop_table("state_laws")
    op.drop_table("agency_guidance")
    op.drop_table("federal_laws")
    op.drop_table("personal_info")

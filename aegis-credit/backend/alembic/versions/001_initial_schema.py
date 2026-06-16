"""Initial schema — all original tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aegis_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("dob", sa.String(), nullable=True),
        sa.Column("ssn_last4", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aegis_clients_id", "aegis_clients", ["id"])
    op.create_index("ix_aegis_clients_email", "aegis_clients", ["email"])

    op.create_table(
        "aegis_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("aegis_clients.id"), nullable=True),
        sa.Column("case_number", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aegis_cases_id", "aegis_cases", ["id"])
    op.create_index("ix_aegis_cases_case_number", "aegis_cases", ["case_number"], unique=True)

    op.create_table(
        "credit_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.String(), nullable=True),
        sa.Column("report_date", sa.String(), nullable=True),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_reports_id", "credit_reports", ["id"])

    op.create_table(
        "tradelines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("credit_reports.id"), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("creditor_name", sa.String(), nullable=True),
        sa.Column("account_number_last4", sa.String(), nullable=True),
        sa.Column("account_type", sa.String(), nullable=True),
        sa.Column("open_date", sa.String(), nullable=True),
        sa.Column("close_date", sa.String(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("credit_limit", sa.Float(), nullable=True),
        sa.Column("payment_status", sa.String(), nullable=True),
        sa.Column("payment_history", sa.Text(), nullable=True),
        sa.Column("derogatory", sa.Boolean(), nullable=True),
        sa.Column("dispute_status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tradelines_id", "tradelines", ["id"])

    op.create_table(
        "tradeline_comparisons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("creditor_name", sa.String(), nullable=True),
        sa.Column("account_number_last4", sa.String(), nullable=True),
        sa.Column("discrepancy_type", sa.String(), nullable=True),
        sa.Column("bureaus_affected", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tradeline_comparisons_id", "tradeline_comparisons", ["id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("tradeline_id", sa.Integer(), sa.ForeignKey("tradelines.id"), nullable=True),
        sa.Column("finding_type", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("fcra_section", sa.String(), nullable=True),
        sa.Column("evidence_ids", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_id", "findings", ["id"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("evidence_type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("collected_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_items_id", "evidence_items", ["id"])

    op.create_table(
        "court_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("aegis_clients.id"), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("record_type", sa.String(), nullable=True),
        sa.Column("court_name", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("docket_number", sa.String(), nullable=True),
        sa.Column("offense_date", sa.String(), nullable=True),
        sa.Column("disposition", sa.String(), nullable=True),
        sa.Column("disposition_date", sa.String(), nullable=True),
        sa.Column("expungement_eligible", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_court_records_id", "court_records", ["id"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("event_date", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("related_finding_id", sa.Integer(), sa.ForeignKey("findings.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timeline_events_id", "timeline_events", ["id"])

    op.create_table(
        "strategy_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("strategy_type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column("estimated_timeline", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_items_id", "strategy_items", ["id"])

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("report_type", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_reports_id", "generated_reports", ["id"])

    op.create_table(
        "dispute_rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("round_number", sa.Integer(), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("sent_date", sa.String(), nullable=True),
        sa.Column("response_due_date", sa.String(), nullable=True),
        sa.Column("response_received_date", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dispute_rounds_id", "dispute_rounds", ["id"])

    op.create_table(
        "dispute_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("dispute_rounds.id"), nullable=True),
        sa.Column("tradeline_id", sa.Integer(), sa.ForeignKey("tradelines.id"), nullable=True),
        sa.Column("creditor_name", sa.String(), nullable=True),
        sa.Column("account_number_last4", sa.String(), nullable=True),
        sa.Column("dispute_reason", sa.String(), nullable=True),
        sa.Column("fcra_basis", sa.String(), nullable=True),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dispute_items_id", "dispute_items", ["id"])

    op.create_table(
        "outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("tradeline_id", sa.Integer(), sa.ForeignKey("tradelines.id"), nullable=True),
        sa.Column("outcome_type", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("achieved_date", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outcomes_id", "outcomes", ["id"])

    op.create_table(
        "learning_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("creditor_name", sa.String(), nullable=True),
        sa.Column("tactic_used", sa.String(), nullable=True),
        sa.Column("fcra_basis", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_entries_id", "learning_entries", ["id"])


def downgrade() -> None:
    op.drop_table("learning_entries")
    op.drop_table("outcomes")
    op.drop_table("dispute_items")
    op.drop_table("dispute_rounds")
    op.drop_table("generated_reports")
    op.drop_table("strategy_items")
    op.drop_table("timeline_events")
    op.drop_table("court_records")
    op.drop_table("evidence_items")
    op.drop_table("findings")
    op.drop_table("tradeline_comparisons")
    op.drop_table("tradelines")
    op.drop_table("credit_reports")
    op.drop_table("aegis_cases")
    op.drop_table("aegis_clients")

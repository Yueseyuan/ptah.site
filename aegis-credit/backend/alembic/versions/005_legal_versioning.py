"""Add legal versioning fields and legal_updates table

Revision ID: 005
Revises: 004
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add versioning columns to federal_laws
    with op.batch_alter_table("federal_laws") as batch_op:
        batch_op.add_column(sa.Column("effective_as_of", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_id", sa.Integer(), sa.ForeignKey("federal_laws.id"), nullable=True))
        batch_op.add_column(sa.Column("version_notes", sa.Text(), nullable=True))

    # Add versioning columns to agency_guidance
    with op.batch_alter_table("agency_guidance") as batch_op:
        batch_op.add_column(sa.Column("effective_as_of", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("superseded", sa.Boolean(), nullable=True, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("version_notes", sa.Text(), nullable=True))

    # Add versioning columns to state_laws
    with op.batch_alter_table("state_laws") as batch_op:
        batch_op.add_column(sa.Column("effective_as_of", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("superseded", sa.Boolean(), nullable=True, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("version_notes", sa.Text(), nullable=True))

    # Create legal_updates table
    op.create_table(
        "legal_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("proposed_changes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_updates_id", "legal_updates", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("legal_updates")
    with op.batch_alter_table("state_laws") as batch_op:
        batch_op.drop_column("version_notes")
        batch_op.drop_column("superseded")
        batch_op.drop_column("effective_as_of")
    with op.batch_alter_table("agency_guidance") as batch_op:
        batch_op.drop_column("version_notes")
        batch_op.drop_column("superseded")
        batch_op.drop_column("effective_as_of")
    with op.batch_alter_table("federal_laws") as batch_op:
        batch_op.drop_column("version_notes")
        batch_op.drop_column("superseded_by_id")
        batch_op.drop_column("effective_as_of")

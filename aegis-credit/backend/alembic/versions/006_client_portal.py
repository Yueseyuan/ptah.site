"""add client portal columns and client_documents table

Revision ID: 006_client_portal
Revises: fbf4b768c89f
Create Date: 2026-06-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_client_portal'
down_revision: Union[str, None] = 'fbf4b768c89f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("aegis_clients") as batch_op:
        batch_op.add_column(sa.Column("portal_user_id", sa.Integer(), nullable=True))

    with op.batch_alter_table("aegis_cases") as batch_op:
        batch_op.add_column(sa.Column("portal_status", sa.String(), nullable=True, server_default="pending"))

    op.create_table(
        "client_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("aegis_cases.id"), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("aegis_clients.id"), nullable=True),
        sa.Column("doc_type", sa.String(), nullable=True),
        sa.Column("bureau", sa.String(), nullable=True),
        sa.Column("original_filename", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("reviewed", sa.Boolean(), default=False),
    )


def downgrade() -> None:
    op.drop_table("client_documents")
    with op.batch_alter_table("aegis_cases") as batch_op:
        batch_op.drop_column("portal_status")
    with op.batch_alter_table("aegis_clients") as batch_op:
        batch_op.drop_column("portal_user_id")

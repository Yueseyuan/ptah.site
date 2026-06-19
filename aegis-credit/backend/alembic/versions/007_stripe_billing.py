"""add stripe billing columns to users

Revision ID: 007_stripe_billing
Revises: 006_client_portal
Create Date: 2026-06-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_stripe_billing'
down_revision: Union[str, None] = '006_client_portal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("stripe_customer_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("stripe_subscription_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("subscription_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("subscription_period_end", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("subscription_period_end")
        batch_op.drop_column("subscription_status")
        batch_op.drop_column("stripe_subscription_id")
        batch_op.drop_column("stripe_customer_id")

"""Merge two independent migration branches into single head

Revision ID: 009_merge_heads
Revises: 007_stripe_billing, 005
Create Date: 2026-06-24

"""
from typing import Sequence, Union

revision: str = '009_merge_heads'
down_revision: Union[str, tuple, None] = ('007_stripe_billing', '005')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

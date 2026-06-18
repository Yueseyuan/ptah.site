"""add_dispute_recipient_tracking_fields

Revision ID: fbf4b768c89f
Revises: 5efe1b9e82b5
Create Date: 2026-06-18 13:38:30.584030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbf4b768c89f'
down_revision: Union[str, None] = '5efe1b9e82b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dispute_rounds') as batch_op:
        batch_op.add_column(sa.Column('recipient_type', sa.String(), nullable=True, server_default='bureau'))
        batch_op.add_column(sa.Column('recipient_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('recipient_address', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('certified_mail_tracking', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('dispute_rounds') as batch_op:
        batch_op.drop_column('certified_mail_tracking')
        batch_op.drop_column('recipient_address')
        batch_op.drop_column('recipient_name')
        batch_op.drop_column('recipient_type')

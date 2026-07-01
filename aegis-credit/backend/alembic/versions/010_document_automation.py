"""Add document automation service tables

Revision ID: 010_document_automation
Revises: 009_merge_heads
Create Date: 2026-06-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '010_document_automation'
down_revision: Union[str, None] = '009_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('service_cases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('division_slug', sa.String(), index=True),
        sa.Column('case_number', sa.String(), unique=True, index=True),
        sa.Column('status', sa.String(), server_default='intake'),
        sa.Column('title', sa.String()),
        sa.Column('intake_data', sa.Text()),
        sa.Column('notes', sa.Text()),
        sa.Column('assigned_to', sa.String()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_table('document_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('division_slug', sa.String(), index=True),
        sa.Column('template_type', sa.String(), server_default='generated'),
        sa.Column('name', sa.String()),
        sa.Column('description', sa.Text()),
        sa.Column('content', sa.Text()),
        sa.Column('variables', sa.Text()),
        sa.Column('category', sa.String()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table('service_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('service_case_id', sa.Integer(), sa.ForeignKey('service_cases.id')),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('document_templates.id'), nullable=True),
        sa.Column('division_slug', sa.String()),
        sa.Column('title', sa.String()),
        sa.Column('document_type', sa.String()),
        sa.Column('content', sa.Text()),
        sa.Column('file_path', sa.String()),
        sa.Column('status', sa.String(), server_default='draft'),
        sa.Column('esign_request_id', sa.String(), nullable=True),
        sa.Column('esign_provider', sa.String(), nullable=True),
        sa.Column('ai_generated', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table('appointments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('service_case_id', sa.Integer(), sa.ForeignKey('service_cases.id'), nullable=True),
        sa.Column('division_slug', sa.String()),
        sa.Column('appointment_type', sa.String()),
        sa.Column('scheduled_at', sa.DateTime()),
        sa.Column('duration_minutes', sa.Integer(), server_default='60'),
        sa.Column('location', sa.String()),
        sa.Column('travel_miles', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), server_default='scheduled'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table('service_invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('service_case_id', sa.Integer(), sa.ForeignKey('service_cases.id'), nullable=True),
        sa.Column('invoice_number', sa.String(), unique=True, index=True),
        sa.Column('division_slug', sa.String()),
        sa.Column('line_items', sa.Text()),
        sa.Column('subtotal', sa.Float(), server_default='0'),
        sa.Column('tax_rate', sa.Float(), server_default='0'),
        sa.Column('tax_amount', sa.Float(), server_default='0'),
        sa.Column('total', sa.Float(), server_default='0'),
        sa.Column('status', sa.String(), server_default='draft'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table('attorney_referrals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('service_case_id', sa.Integer(), sa.ForeignKey('service_cases.id'), nullable=True),
        sa.Column('attorney_name', sa.String()),
        sa.Column('attorney_firm', sa.String()),
        sa.Column('attorney_email', sa.String()),
        sa.Column('attorney_phone', sa.String()),
        sa.Column('practice_area', sa.String()),
        sa.Column('reason', sa.Text()),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('referral_letter_path', sa.String(), nullable=True),
        sa.Column('notes', sa.Text()),
        sa.Column('referred_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table('notary_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('aegis_clients.id')),
        sa.Column('service_case_id', sa.Integer(), sa.ForeignKey('service_cases.id'), nullable=True),
        sa.Column('journal_number', sa.String(), unique=True, index=True),
        sa.Column('document_type', sa.String()),
        sa.Column('signer_name', sa.String()),
        sa.Column('signer_id_type', sa.String()),
        sa.Column('signer_id_number', sa.String()),
        sa.Column('signer_id_expiry', sa.String()),
        sa.Column('num_signers', sa.Integer(), server_default='1'),
        sa.Column('num_witnesses', sa.Integer(), server_default='0'),
        sa.Column('notarized_at', sa.DateTime()),
        sa.Column('location', sa.String()),
        sa.Column('travel_miles', sa.Float(), nullable=True),
        sa.Column('fee_charged', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('notary_logs')
    op.drop_table('attorney_referrals')
    op.drop_table('service_invoices')
    op.drop_table('appointments')
    op.drop_table('service_documents')
    op.drop_table('document_templates')
    op.drop_table('service_cases')

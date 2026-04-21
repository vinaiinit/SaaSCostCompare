"""add_license_analyses_table

Revision ID: a1b2c3d4e5f6
Revises: 83662dcc9c49
Create Date: 2026-04-21

Add license_analyses table for storing vendor API license utilization results.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '83662dcc9c49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'license_analyses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('vendor_name', sa.String(), nullable=True, index=True),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('license_analyses')

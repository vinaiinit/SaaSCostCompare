"""Add subscriptions table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, index=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), index=True),
        sa.Column("stripe_customer_id", sa.String(), unique=True, nullable=True, index=True),
        sa.Column("stripe_subscription_id", sa.String(), unique=True, nullable=True, index=True),
        sa.Column("plan", sa.String(), server_default="free"),
        sa.Column("status", sa.String(), server_default="active"),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("reports_used_this_period", sa.Integer(), server_default="0"),
        sa.Column("reports_limit", sa.Integer(), server_default="0"),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("subscriptions")

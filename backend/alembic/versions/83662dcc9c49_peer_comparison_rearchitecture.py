"""peer_comparison_rearchitecture

Revision ID: 83662dcc9c49
Revises:
Create Date: 2026-04-16 21:30:30.300152

Migrate from AI-analysis model to peer-to-peer comparison model:
- Rename organizations.domain → organizations.industry
- Add size_band, revenue_band columns to organizations
- Add password_reset_tokens table (if not exists)
- Add contact_inquiries table (if not exists)
- Add contract_line_items table
- Add vendor_catalog table
- Add product_catalog table
- Add data_coverage_stats table
- Add campaign_submissions table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '83662dcc9c49'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists (works for both SQLite and PostgreSQL)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # --- Organizations: rename domain → industry, add bands ---
    if _table_exists("organizations"):
        if _column_exists("organizations", "domain") and not _column_exists("organizations", "industry"):
            if is_sqlite:
                # SQLite doesn't support ALTER COLUMN RENAME, so add new column and copy
                op.add_column("organizations", sa.Column("industry", sa.String(), nullable=True))
                op.execute("UPDATE organizations SET industry = domain")
                # Can't drop column in older SQLite, leave domain in place
            else:
                # PostgreSQL supports RENAME COLUMN
                op.alter_column("organizations", "domain", new_column_name="industry")

        if not _column_exists("organizations", "size_band"):
            op.add_column("organizations", sa.Column("size_band", sa.String(), nullable=True))
        if not _column_exists("organizations", "revenue_band"):
            op.add_column("organizations", sa.Column("revenue_band", sa.String(), nullable=True))

    # --- Password reset tokens (may already exist from earlier feature) ---
    if not _table_exists("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("token", sa.String(), unique=True, index=True),
            sa.Column("expires_at", sa.DateTime()),
            sa.Column("used", sa.Boolean(), default=False),
            sa.Column("created_at", sa.DateTime()),
        )

    # --- Contact inquiries (may already exist) ---
    if not _table_exists("contact_inquiries"):
        op.create_table(
            "contact_inquiries",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String()),
            sa.Column("email", sa.String()),
            sa.Column("company", sa.String()),
            sa.Column("message", sa.Text()),
            sa.Column("created_at", sa.DateTime()),
        )

    # --- Contract line items (core new table) ---
    if not _table_exists("contract_line_items"):
        op.create_table(
            "contract_line_items",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("upload_id", sa.String(), sa.ForeignKey("reports.id"), index=True),
            sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), index=True),
            sa.Column("vendor_name", sa.String(), index=True),
            sa.Column("product_name", sa.String(), index=True),
            sa.Column("sku", sa.String(), nullable=True),
            sa.Column("quantity", sa.Integer(), default=1),
            sa.Column("unit_price", sa.Float(), default=0.0),
            sa.Column("total_cost", sa.Float(), default=0.0),
            sa.Column("billing_frequency", sa.String(), default="annual"),
            sa.Column("currency", sa.String(), default="USD"),
            sa.Column("contract_start_date", sa.Date(), nullable=True),
            sa.Column("contract_end_date", sa.Date(), nullable=True),
            sa.Column("cost_per_unit_annual", sa.Float(), default=0.0),
            sa.Column("total_cost_annual", sa.Float(), default=0.0),
            sa.Column("extraction_source", sa.String(), default="csv"),
            sa.Column("extraction_confidence", sa.Float(), nullable=True),
            sa.Column("is_validated", sa.Boolean(), default=False),
            sa.Column("created_at", sa.DateTime()),
        )

    # --- Vendor catalog ---
    if not _table_exists("vendor_catalog"):
        op.create_table(
            "vendor_catalog",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("canonical_name", sa.String(), unique=True, index=True),
            sa.Column("aliases", sa.JSON(), default=[]),
            sa.Column("category", sa.String()),
            sa.Column("created_at", sa.DateTime()),
        )

    # --- Product catalog ---
    if not _table_exists("product_catalog"):
        op.create_table(
            "product_catalog",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendor_catalog.id"), index=True),
            sa.Column("canonical_name", sa.String(), index=True),
            sa.Column("aliases", sa.JSON(), default=[]),
            sa.Column("created_at", sa.DateTime()),
        )

    # --- Data coverage stats ---
    if not _table_exists("data_coverage_stats"):
        op.create_table(
            "data_coverage_stats",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("vendor_name", sa.String(), index=True),
            sa.Column("product_name", sa.String(), nullable=True),
            sa.Column("industry", sa.String(), nullable=True),
            sa.Column("size_band", sa.String(), nullable=True),
            sa.Column("org_count", sa.Integer(), default=0),
            sa.Column("line_item_count", sa.Integer(), default=0),
            sa.Column("p25_cost", sa.Float(), nullable=True),
            sa.Column("median_cost", sa.Float(), nullable=True),
            sa.Column("p75_cost", sa.Float(), nullable=True),
            sa.Column("last_updated", sa.DateTime()),
        )

    # --- Campaign submissions ---
    if not _table_exists("campaign_submissions"):
        op.create_table(
            "campaign_submissions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("company_name", sa.String(), nullable=True),
            sa.Column("industry", sa.String(), nullable=True),
            sa.Column("company_size", sa.Integer(), nullable=True),
            sa.Column("vendor_name", sa.String()),
            sa.Column("file_path", sa.String()),
            sa.Column("status", sa.String(), default="submitted"),
            sa.Column("line_items_extracted", sa.Integer(), default=0),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("converted_to_org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # Drop new tables
    for table in ["campaign_submissions", "data_coverage_stats", "product_catalog",
                   "vendor_catalog", "contract_line_items"]:
        if _table_exists(table):
            op.drop_table(table)

    # Revert organizations columns
    if _table_exists("organizations"):
        if not is_sqlite:
            if _column_exists("organizations", "industry"):
                op.alter_column("organizations", "industry", new_column_name="domain")
            if _column_exists("organizations", "size_band"):
                op.drop_column("organizations", "size_band")
            if _column_exists("organizations", "revenue_band"):
                op.drop_column("organizations", "revenue_band")

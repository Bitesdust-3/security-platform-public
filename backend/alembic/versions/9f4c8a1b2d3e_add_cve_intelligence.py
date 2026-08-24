"""add CVE intelligence repository

Revision ID: 9f4c8a1b2d3e
Revises: 8d2a1f3c4b5e
"""
from alembic import op
import sqlalchemy as sa

revision = "9f4c8a1b2d3e"
down_revision = "8d2a1f3c4b5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cve_intelligence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cve_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("affected_products", sa.Text(), nullable=True),
        sa.Column("references", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("cve_id", name="uq_cve_intelligence_cve_id"),
    )
    op.create_index("ix_cve_intelligence_cve_id", "cve_intelligence", ["cve_id"], unique=True)
    op.create_index("ix_cve_intelligence_severity", "cve_intelligence", ["severity"])
    op.create_index("ix_cve_intelligence_published_at", "cve_intelligence", ["published_at"])
    op.create_index("ix_cve_intelligence_last_modified_at", "cve_intelligence", ["last_modified_at"])


def downgrade() -> None:
    op.drop_table("cve_intelligence")

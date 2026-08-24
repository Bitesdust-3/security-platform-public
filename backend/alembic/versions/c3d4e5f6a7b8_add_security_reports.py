"""add security report snapshots

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGTEXT
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None
def upgrade() -> None:
    html_type = LONGTEXT() if op.get_bind().dialect.name == "mysql" else sa.Text()
    op.create_table("security_reports", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("report_name", sa.String(160), nullable=False), sa.Column("period_start", sa.DateTime(), nullable=False), sa.Column("period_end", sa.DateTime(), nullable=False), sa.Column("generated_at", sa.DateTime(), nullable=False), sa.Column("asset_count", sa.Integer(), nullable=False), sa.Column("online_asset_count", sa.Integer(), nullable=False), sa.Column("high_risk_asset_count", sa.Integer(), nullable=False), sa.Column("vulnerability_count", sa.Integer(), nullable=False), sa.Column("cve_count", sa.Integer(), nullable=False), sa.Column("high_risk_vulnerability_count", sa.Integer(), nullable=False), sa.Column("risk_distribution", sa.Text(), nullable=False), sa.Column("scan_statistics", sa.Text(), nullable=False), sa.Column("vulnerability_trend", sa.Text(), nullable=False), sa.Column("top_risk_assets", sa.Text(), nullable=False), sa.Column("recommendations", sa.Text(), nullable=False), sa.Column("report_html", html_type, nullable=True), sa.Column("created_by", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["created_by"], ["users.id"]))
    op.create_index("ix_security_reports_generated_at", "security_reports", ["generated_at"]); op.create_index("ix_security_reports_created_by", "security_reports", ["created_by"])
def downgrade() -> None: op.drop_table("security_reports")

"""add persistent scan schedules

Revision ID: 8d2a1f3c4b5e
Revises: e026fb199153
"""
from alembic import op
import sqlalchemy as sa

revision = "8d2a1f3c4b5e"
down_revision = "e026fb199153"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("scan_type", sa.String(length=32), nullable=False),
        sa.Column("schedule_type", sa.String(length=16), nullable=False),
        sa.Column("execute_at", sa.DateTime(), nullable=True),
        sa.Column("cron_expression", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    for name, column in (("ix_scan_schedules_asset_id", "asset_id"), ("ix_scan_schedules_created_by", "created_by"), ("ix_scan_schedules_next_run_at", "next_run_at"), ("ix_scan_schedules_status", "status")):
        op.create_index(name, "scan_schedules", [column])


def downgrade() -> None:
    op.drop_table("scan_schedules")

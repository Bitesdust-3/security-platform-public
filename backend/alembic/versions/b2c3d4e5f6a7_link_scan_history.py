"""link scan executions to schedules

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("scan_tasks")}
    indexes = {index["name"] for index in inspector.get_indexes("scan_tasks")}
    if "schedule_id" not in columns:
        op.add_column("scan_tasks", sa.Column("schedule_id", sa.Integer(), nullable=True))
    if "ix_scan_tasks_schedule_id" not in indexes:
        op.create_index("ix_scan_tasks_schedule_id", "scan_tasks", ["schedule_id"])
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_scan_tasks_schedule", "scan_tasks", "scan_schedules", ["schedule_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_scan_tasks_schedule", "scan_tasks", type_="foreignkey")
    op.drop_index("ix_scan_tasks_schedule_id", table_name="scan_tasks")
    op.drop_column("scan_tasks", "schedule_id")

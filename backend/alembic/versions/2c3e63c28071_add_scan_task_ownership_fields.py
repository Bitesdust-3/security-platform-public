"""add scan task ownership fields

Revision ID: 2c3e63c28071
Revises: f1fc5988e164
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '2c3e63c28071'
down_revision: Union[str, Sequence[str], None] = 'f1fc5988e164'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL cannot recreate scan_tasks while scan_results has a foreign key to
    # it. Apply an in-place, data-preserving conversion instead. SQLite keeps
    # the original batch path below for its limited ALTER TABLE support.
    if op.get_bind().dialect.name == "mysql":
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        columns = {column["name"] for column in inspector.get_columns("scan_tasks")}

        for name, column_type in (
            ("task_name", sa.String(length=128)),
            ("target", sa.String(length=255)),
            ("scan_type", sa.String(length=32)),
        ):
            if name not in columns:
                op.add_column("scan_tasks", sa.Column(name, column_type, nullable=True))
        if "result_summary" not in columns:
            op.add_column("scan_tasks", sa.Column("result_summary", sa.Text(), nullable=True))
        if "created_by" not in columns:
            op.add_column("scan_tasks", sa.Column("created_by", sa.Integer(), nullable=True))

        # The source columns were non-null in the previous schema, so every
        # existing row can be retained before the replacement columns become
        # required.
        bind.execute(sa.text("""
            UPDATE scan_tasks
            SET task_name = name,
                target = target_scope,
                scan_type = scanner_type,
                created_by = requested_by
        """))
        for name, column_type in (
            ("task_name", sa.String(length=128)),
            ("target", sa.String(length=255)),
            ("scan_type", sa.String(length=32)),
        ):
            op.alter_column("scan_tasks", name, existing_type=column_type, nullable=False)

        # Drop the old child-side user foreign key before removing requested_by.
        for foreign_key in inspector.get_foreign_keys("scan_tasks"):
            if foreign_key["constrained_columns"] == ["requested_by"] and foreign_key["name"]:
                op.drop_constraint(foreign_key["name"], "scan_tasks", type_="foreignkey")
        for name in ("scanner_type", "requested_by", "name", "target_scope"):
            if name in columns:
                op.drop_column("scan_tasks", name)

        inspector = sa.inspect(bind)
        indexes = {index["name"] for index in inspector.get_indexes("scan_tasks")}
        if "ix_scan_tasks_created_by" not in indexes:
            op.create_index("ix_scan_tasks_created_by", "scan_tasks", ["created_by"], unique=False)
        foreign_keys = inspector.get_foreign_keys("scan_tasks")
        if not any(foreign_key["constrained_columns"] == ["created_by"] for foreign_key in foreign_keys):
            op.create_foreign_key("fk_scan_tasks_created_by_users", "scan_tasks", "users", ["created_by"], ["id"])
        return

    with op.batch_alter_table("scan_tasks", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("task_name", sa.String(length=128), nullable=False))
        batch_op.add_column(sa.Column("target", sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column("scan_type", sa.String(length=32), nullable=False))
        batch_op.add_column(sa.Column("result_summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_scan_tasks_created_by", ["created_by"], unique=False)
        batch_op.create_foreign_key("fk_scan_tasks_created_by_users", "users", ["created_by"], ["id"])
        batch_op.drop_column("scanner_type")
        batch_op.drop_column("requested_by")
        batch_op.drop_column("name")
        batch_op.drop_column("target_scope")


def downgrade() -> None:
    with op.batch_alter_table("scan_tasks", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("target_scope", sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column("name", sa.String(length=128), nullable=False))
        batch_op.add_column(sa.Column("requested_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("scanner_type", sa.String(length=32), nullable=False))
        batch_op.create_foreign_key("fk_scan_tasks_requested_by_users", "users", ["requested_by"], ["id"])
        batch_op.drop_index("ix_scan_tasks_created_by")
        batch_op.drop_column("created_by")
        batch_op.drop_column("result_summary")
        batch_op.drop_column("scan_type")
        batch_op.drop_column("target")
        batch_op.drop_column("task_name")

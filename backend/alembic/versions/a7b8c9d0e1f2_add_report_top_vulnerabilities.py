"""Add a point-in-time Top vulnerability snapshot to security reports."""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL does not permit a DEFAULT value on TEXT columns.  Add the column
    # nullable first, backfill existing snapshots, then make it mandatory.
    op.add_column("security_reports", sa.Column("top_vulnerabilities", sa.Text(), nullable=True))
    op.execute("UPDATE security_reports SET top_vulnerabilities = '[]' WHERE top_vulnerabilities IS NULL")
    op.alter_column("security_reports", "top_vulnerabilities", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.drop_column("security_reports", "top_vulnerabilities")

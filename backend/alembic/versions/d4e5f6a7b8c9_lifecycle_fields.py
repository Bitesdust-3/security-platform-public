"""add lifecycle fields for vulnerabilities and reports"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vulnerabilities", sa.Column("fixed_at", sa.DateTime(), nullable=True))
    op.add_column("vulnerabilities", sa.Column("remark", sa.Text(), nullable=True))
    op.add_column("security_reports", sa.Column("status", sa.String(16), nullable=False, server_default="generated"))
    op.add_column("security_reports", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("security_reports", sa.Column("archived_by", sa.Integer(), nullable=True))
    op.create_index("ix_security_reports_status", "security_reports", ["status"])
    op.create_index("ix_security_reports_archived_by", "security_reports", ["archived_by"])
    op.create_foreign_key("fk_security_reports_archived_by_users", "security_reports", "users", ["archived_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_security_reports_archived_by_users", "security_reports", type_="foreignkey")
    op.drop_index("ix_security_reports_archived_by", table_name="security_reports")
    op.drop_index("ix_security_reports_status", table_name="security_reports")
    op.drop_column("security_reports", "archived_by")
    op.drop_column("security_reports", "archived_at")
    op.drop_column("security_reports", "status")
    op.drop_column("vulnerabilities", "remark")
    op.drop_column("vulnerabilities", "fixed_at")

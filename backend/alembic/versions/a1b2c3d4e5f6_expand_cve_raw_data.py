"""expand CVE raw JSON storage for MySQL

Revision ID: a1b2c3d4e5f6
Revises: 9f4c8a1b2d3e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "a1b2c3d4e5f6"
down_revision = "9f4c8a1b2d3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "mysql":
        op.alter_column("cve_intelligence", "raw_data", existing_type=sa.Text(), type_=mysql.LONGTEXT(), existing_nullable=True)


def downgrade() -> None:
    if op.get_bind().dialect.name == "mysql":
        op.alter_column("cve_intelligence", "raw_data", existing_type=mysql.LONGTEXT(), type_=sa.Text(), existing_nullable=True)

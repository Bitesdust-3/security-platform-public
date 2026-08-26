"""add port state to structured scan results"""

from alembic import op
import sqlalchemy as sa


revision = "f6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scan_results", sa.Column("port_state", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_results", "port_state")

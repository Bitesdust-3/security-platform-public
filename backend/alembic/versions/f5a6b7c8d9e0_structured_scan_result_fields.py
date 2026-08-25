"""add structured fields to scan results"""
from alembic import op
import sqlalchemy as sa


revision = "f5a6b7c8d9e0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scan_results", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("scan_results", sa.Column("port", sa.Integer(), nullable=True))
    op.add_column("scan_results", sa.Column("protocol", sa.String(16), nullable=True))
    op.add_column("scan_results", sa.Column("service_name", sa.String(128), nullable=True))
    op.add_column("scan_results", sa.Column("product_name", sa.String(128), nullable=True))
    op.add_column("scan_results", sa.Column("service_version", sa.String(128), nullable=True))
    op.create_index("ix_scan_results_ip_address", "scan_results", ["ip_address"])
    op.create_index("ix_scan_results_port", "scan_results", ["port"])
    op.create_index("ix_scan_results_service_name", "scan_results", ["service_name"])
    op.create_index("ix_scan_results_product_name", "scan_results", ["product_name"])


def downgrade() -> None:
    op.drop_index("ix_scan_results_product_name", table_name="scan_results")
    op.drop_index("ix_scan_results_service_name", table_name="scan_results")
    op.drop_index("ix_scan_results_port", table_name="scan_results")
    op.drop_index("ix_scan_results_ip_address", table_name="scan_results")
    op.drop_column("scan_results", "service_version")
    op.drop_column("scan_results", "product_name")
    op.drop_column("scan_results", "service_name")
    op.drop_column("scan_results", "protocol")
    op.drop_column("scan_results", "port")
    op.drop_column("scan_results", "ip_address")

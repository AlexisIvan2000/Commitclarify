"""Reservations de quota sur l'etape IA

Revision ID: 0004_quota_reservations
Revises: 0003_scan_phase
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0004_quota_reservations"
down_revision: str | None = "0003_scan_phase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_log", sa.Column("analysis_id", sa.Uuid(), nullable=True))
    op.add_column(
        "analysis_log",
        sa.Column("state", sa.String(length=12), nullable=False, server_default="committed"),
    )
    op.add_column("analysis_log", sa.Column("expires_at", sa.DateTime(), nullable=True))

    op.create_index(
        "uq_analysis_log_analysis_id", "analysis_log", ["analysis_id"], unique=True,
    )
    op.create_index(
        "ix_analysis_log_state_expires_at", "analysis_log", ["state", "expires_at"],
    )


def downgrade() -> None:
    op.execute("DELETE FROM analysis_log WHERE state = 'reserved'")

    op.drop_index("ix_analysis_log_state_expires_at", table_name="analysis_log")
    op.drop_index("uq_analysis_log_analysis_id", table_name="analysis_log")

    op.drop_column("analysis_log", "expires_at")
    op.drop_column("analysis_log", "state")
    op.drop_column("analysis_log", "analysis_id")

"""Provenance et couverture d'un rapport de scan

Revision ID: 0005_report_provenance
Revises: 0004_quota_reservations
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0005_report_provenance"
down_revision: str | None = "0004_quota_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("coverage", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "coverage")

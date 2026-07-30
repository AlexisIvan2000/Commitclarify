"""Langue de generation des analyses

Revision ID: 0002_analysis_language
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0002_analysis_language"
down_revision: str | None = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("language", sa.String(length=5), nullable=False, server_default="fr"),
    )


def downgrade() -> None:
    op.drop_column("analyses", "language")

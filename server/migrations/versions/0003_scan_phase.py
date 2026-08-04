"""Phase de scan deterministe et cache de resultats

Revision ID: 0003_scan_phase
Revises: 0002_analysis_language
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0003_scan_phase"
down_revision: str | None = "0002_analysis_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("repo_id", sa.Integer(), nullable=True))
    op.add_column("analyses", sa.Column("scan_version", sa.Integer(), nullable=True))
    op.add_column("analyses", sa.Column("config_hash", sa.String(length=32), nullable=True))
    op.add_column("analyses", sa.Column("phase_started_at", sa.DateTime(), nullable=True))

    op.add_column("analysis_results", sa.Column("metrics", sa.JSON(), nullable=True))

    op.create_table(
        "scan_cache",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("scan_version", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "repo_id", "commit_sha", "scan_version", "config_hash", "language",
            name="uq_scan_cache_key",
        ),
    )
    op.create_index("ix_scan_cache_created_at", "scan_cache", ["created_at"])

    op.execute("UPDATE analyses SET status = 'scanning' WHERE status = 'processing'")


def downgrade() -> None:
    op.execute("UPDATE analyses SET status = 'processing' WHERE status IN ('scanning', 'scanned', 'analyzing')")

    op.drop_index("ix_scan_cache_created_at", table_name="scan_cache")
    op.drop_table("scan_cache")

    op.drop_column("analysis_results", "metrics")

    op.drop_column("analyses", "phase_started_at")
    op.drop_column("analyses", "config_hash")
    op.drop_column("analyses", "scan_version")
    op.drop_column("analyses", "repo_id")

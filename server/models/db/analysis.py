import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.clock import utcnow
from core.database import Base

if TYPE_CHECKING:
    from models.db.user import User


class Analysis(Base):
    __tablename__ = "analyses"

    id               : Mapped[uuid.UUID]       = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id          : Mapped[uuid.UUID]       = mapped_column(ForeignKey("users.id"))
    repo_name        : Mapped[str]             = mapped_column(String(200))
    repo_id          : Mapped[int | None]      = mapped_column(Integer, nullable=True)
    repo_sha         : Mapped[str | None]      = mapped_column(String(40), nullable=True)
    status           : Mapped[str]             = mapped_column(String(20), default="pending")
    language         : Mapped[str]             = mapped_column(String(5), default="fr", server_default="fr")
    scan_version     : Mapped[int | None]      = mapped_column(Integer, nullable=True)
    config_hash      : Mapped[str | None]      = mapped_column(String(32), nullable=True)
    coverage         : Mapped[dict | None]     = mapped_column(JSON, nullable=True)
    created_at       : Mapped[datetime]        = mapped_column(DateTime, default=utcnow)
    phase_started_at : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at     : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    user:    Mapped["User"]                 = relationship(back_populates="analyses")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id              : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id     : Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id"))
    aspect          : Mapped[str]       = mapped_column(String(50))
    status          : Mapped[str]       = mapped_column(String(20))
    issues          : Mapped[list]        = mapped_column(JSON)
    recommendations : Mapped[list]        = mapped_column(JSON)
    metrics         : Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at      : Mapped[datetime]    = mapped_column(DateTime, default=utcnow)

    analysis: Mapped["Analysis"] = relationship(back_populates="results")


class ScanCache(Base):
    __tablename__ = "scan_cache"
    __table_args__ = (
        UniqueConstraint(
            "repo_id", "commit_sha", "scan_version", "config_hash", "language",
            name="uq_scan_cache_key",
        ),
    )

    id           : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repo_id      : Mapped[int]       = mapped_column(Integer, nullable=False)
    commit_sha   : Mapped[str]       = mapped_column(String(40), nullable=False)
    scan_version : Mapped[int]       = mapped_column(Integer, nullable=False)
    config_hash  : Mapped[str]       = mapped_column(String(32), nullable=False)
    language     : Mapped[str]       = mapped_column(String(5), nullable=False)
    payload      : Mapped[dict]      = mapped_column(JSON, nullable=False)
    created_at   : Mapped[datetime]  = mapped_column(DateTime, default=utcnow)


class AnalysisLog(Base):
    __tablename__ = "analysis_log"

    id          : Mapped[uuid.UUID]        = mapped_column(primary_key=True, default=uuid.uuid4)
    github_id   : Mapped[int]              = mapped_column(Integer, nullable=False, index=True)
    analysis_id : Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, unique=True)
    state       : Mapped[str]              = mapped_column(
        String(12), default="committed", server_default="committed",
    )
    expires_at  : Mapped[datetime | None]  = mapped_column(DateTime, nullable=True)
    created_at  : Mapped[datetime]         = mapped_column(DateTime, default=utcnow)

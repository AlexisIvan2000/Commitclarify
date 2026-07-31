import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.clock import utcnow
from core.database import Base

if TYPE_CHECKING:
    from models.db.user import User


class Analysis(Base):
    __tablename__ = "analyses"

    id           : Mapped[uuid.UUID]       = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id      : Mapped[uuid.UUID]       = mapped_column(ForeignKey("users.id"))
    repo_name    : Mapped[str]             = mapped_column(String(200))
    repo_sha     : Mapped[str | None]      = mapped_column(String(40), nullable=True)
    status       : Mapped[str]             = mapped_column(String(20), default="pending")
    language     : Mapped[str]             = mapped_column(String(5), default="fr", server_default="fr")
    created_at   : Mapped[datetime]        = mapped_column(DateTime, default=utcnow)
    completed_at : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

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
    issues          : Mapped[list]      = mapped_column(JSON)
    recommendations : Mapped[list]      = mapped_column(JSON)
    created_at      : Mapped[datetime]  = mapped_column(DateTime, default=utcnow)

    analysis: Mapped["Analysis"] = relationship(back_populates="results")


class AnalysisLog(Base):
    __tablename__ = "analysis_log"

    id         : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    github_id  : Mapped[int]       = mapped_column(Integer, nullable=False, index=True)
    created_at : Mapped[datetime]  = mapped_column(DateTime, default=utcnow)

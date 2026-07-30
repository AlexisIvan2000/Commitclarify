import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.clock import utcnow
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id:           Mapped[uuid.UUID]  = mapped_column(primary_key=True, default=uuid.uuid4)
    github_id:    Mapped[int]        = mapped_column(Integer, unique=True, nullable=False)
    login:        Mapped[str]        = mapped_column(String(100))
    username:     Mapped[str]        = mapped_column(String(100))
    avatar_url:   Mapped[str]        = mapped_column(Text, nullable=True)
    email:        Mapped[str]        = mapped_column(String(200), nullable=True)
    access_token: Mapped[str]        = mapped_column(Text)
    created_at:   Mapped[datetime]   = mapped_column(DateTime, default=utcnow)
    updated_at:   Mapped[datetime]   = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    auth_codes:     Mapped[list["AuthCode"]]     = relationship(back_populates="user")
    analyses:       Mapped[list["Analysis"]]     = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id:         Mapped[uuid.UUID]       = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID]       = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str]             = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]        = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]        = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class AuthCode(Base):
    __tablename__ = "auth_codes"

    id:            Mapped[uuid.UUID]       = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id:       Mapped[uuid.UUID]       = mapped_column(ForeignKey("users.id"))
    code_hash:     Mapped[str]             = mapped_column(String(64), unique=True, index=True)
    access_token:  Mapped[str]             = mapped_column(Text)
    refresh_token: Mapped[str]             = mapped_column(Text)
    expires_at:    Mapped[datetime]        = mapped_column(DateTime)
    used_at:       Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at:    Mapped[datetime]        = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="auth_codes")


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

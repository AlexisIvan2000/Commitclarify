import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.clock import utcnow
from core.database import Base

if TYPE_CHECKING:
    from models.db.user import User


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

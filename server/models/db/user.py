import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.clock import utcnow
from core.database import Base

if TYPE_CHECKING:
    from models.db.analysis import Analysis
    from models.db.token import AuthCode, RefreshToken


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

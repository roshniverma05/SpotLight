from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class GitHubAuthorization(Base):
    """Stores a user's authorized GitHub connection."""

    __tablename__ = "github_authorizations"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    github_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    github_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    access_token_encrypted: Mapped[str] = mapped_column(
        String(4096),
        nullable=False,
    )

    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        String(4096),
        nullable=True,
    )

    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
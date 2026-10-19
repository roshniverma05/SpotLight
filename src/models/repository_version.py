from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class RepositoryVersion(Base):
    __tablename__ = "repository_versions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    repository_id: Mapped[UUID] = mapped_column(
        ForeignKey("repositories.id"),
        nullable=False,
        index=True,
    )

    commit_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        nullable=False,
        unique=True,
    )

    workspace_path: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "commit_sha",
            name="uq_repository_commit",
        ),
    )
"""add repository persistence

Revision ID: b3d343c09665
Revises: ad75a6877d19
Create Date: 2026-10-02 21:48:40.315458

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3d343c09665"
down_revision: Union[str, Sequence[str], None] = "ad75a6877d19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create repository persistence tables."""

    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repository", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "owner",
            "repository",
            name="uq_user_repository",
        ),
    )

    op.create_index(
        op.f("ix_repositories_user_id"),
        "repositories",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "repository_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "workspace_path",
            sa.String(length=2048),
            nullable=False,
        ),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_id",
            "commit_sha",
            name="uq_repository_commit",
        ),
        sa.UniqueConstraint("workspace_id"),
    )

    op.create_index(
        op.f("ix_repository_versions_repository_id"),
        "repository_versions",
        ["repository_id"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column(
            "repository_version_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "task_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["repository_version_id"],
            ["repository_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_tasks_repository_id"),
        "tasks",
        ["repository_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_tasks_repository_version_id"),
        "tasks",
        ["repository_version_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_tasks_user_id"),
        "tasks",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove repository persistence tables."""

    op.drop_index(
        op.f("ix_tasks_user_id"),
        table_name="tasks",
    )

    op.drop_index(
        op.f("ix_tasks_repository_version_id"),
        table_name="tasks",
    )

    op.drop_index(
        op.f("ix_tasks_repository_id"),
        table_name="tasks",
    )

    op.drop_table("tasks")

    op.drop_index(
        op.f("ix_repository_versions_repository_id"),
        table_name="repository_versions",
    )

    op.drop_table("repository_versions")

    op.drop_index(
        op.f("ix_repositories_user_id"),
        table_name="repositories",
    )

    op.drop_table("repositories")
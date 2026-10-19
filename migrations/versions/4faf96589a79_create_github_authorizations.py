"""create github authorizations

Revision ID: 4faf96589a79
Revises: df27597d38f3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4faf96589a79"
down_revision: Union[str, Sequence[str], None] = "df27597d38f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the github_authorizations table."""

    op.create_table(
        "github_authorizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "github_user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "github_username",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "access_token_encrypted",
            sa.String(length=4096),
            nullable=False,
        ),
        sa.Column(
            "refresh_token_encrypted",
            sa.String(length=4096),
            nullable=True,
        ),
        sa.Column(
            "access_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "refresh_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
        sa.UniqueConstraint("user_id"),
    )

    op.create_index(
        "ix_github_authorizations_user_id",
        "github_authorizations",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the github_authorizations table."""

    op.drop_index(
        "ix_github_authorizations_user_id",
        table_name="github_authorizations",
    )

    op.drop_table("github_authorizations")
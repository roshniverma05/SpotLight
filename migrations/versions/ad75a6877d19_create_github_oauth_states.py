"""create github oauth states

Revision ID: ad75a6877d19
Revises: 4faf96589a79
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ad75a6877d19"
down_revision: Union[str, Sequence[str], None] = "4faf96589a79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the github_oauth_states table."""

    op.create_table(
        "github_oauth_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state"),
    )

    op.create_index(
        "ix_github_oauth_states_state",
        "github_oauth_states",
        ["state"],
        unique=False,
    )

    op.create_index(
        "ix_github_oauth_states_user_id",
        "github_oauth_states",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the github_oauth_states table."""

    op.drop_index(
        "ix_github_oauth_states_user_id",
        table_name="github_oauth_states",
    )

    op.drop_index(
        "ix_github_oauth_states_state",
        table_name="github_oauth_states",
    )

    op.drop_table("github_oauth_states")
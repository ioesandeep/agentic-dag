"""Adds the pull request url column to work trees."""

import sqlalchemy as sa
from alembic import op

revision: str = "b8d0f2a4c6e8"
down_revision: str | None = "a7c9d1e3f5b7"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Adds the pull request url column to work trees, backfilling existing rows with empty."""
    op.add_column(
        "work_trees",
        sa.Column("pr_url", sa.String(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Drops the pull request url column from work trees."""
    op.drop_column("work_trees", "pr_url")

"""Adds the head SHA column to work trees."""

import sqlalchemy as sa
from alembic import op

revision: str = "a7c9d1e3f5b7"
down_revision: str | None = "f6b8c0d2e4a6"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Adds the head SHA column to work trees."""
    op.add_column(
        "work_trees",
        sa.Column("head_sha", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drops the head SHA column from work trees."""
    op.drop_column("work_trees", "head_sha")

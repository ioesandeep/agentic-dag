"""Adds the pull request settled and learnings extracted columns to nodes."""

import sqlalchemy as sa
from alembic import op

revision: str = "f6b8c0d2e4a6"
down_revision: str | None = "e5a7b9c1d3f5"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Adds the two learning extraction columns to nodes, leaving both null on existing rows."""
    op.add_column(
        "nodes",
        sa.Column("pull_request_settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("learnings_extracted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drops the two learning extraction columns from nodes."""
    op.drop_column("nodes", "learnings_extracted_at")
    op.drop_column("nodes", "pull_request_settled_at")

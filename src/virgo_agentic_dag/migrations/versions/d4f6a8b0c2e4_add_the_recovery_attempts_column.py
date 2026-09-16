"""Adds the recovery attempts column to nodes."""

import sqlalchemy as sa
from alembic import op

revision: str = "d4f6a8b0c2e4"
down_revision: str | None = "c3e5a7b9d1f2"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Adds the recovery attempts column to nodes, backfilling existing rows with three."""
    op.add_column(
        "nodes",
        sa.Column(
            "recovery_attempts_allowed",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )


def downgrade() -> None:
    """Drops the recovery attempts column from nodes."""
    op.drop_column("nodes", "recovery_attempts_allowed")

"""Adds a resume time for pending nodes."""

from alembic import op
from sqlalchemy import Column, DateTime

revision: str = "a7c9e1f3b5d7"
down_revision: str | None = "b8d0f2a4c6e8"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Adds the nullable node resume time."""
    resume_at_type = DateTime(timezone=True)
    resume_at_column = Column("resume_at", resume_at_type, nullable=True)
    op.add_column("nodes", resume_at_column)


def downgrade() -> None:
    """Removes the node resume time."""
    op.drop_column("nodes", "resume_at")

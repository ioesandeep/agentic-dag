"""Creates the recovery_session table."""

import sqlalchemy as sa
from alembic import op

revision: str = "e5a7b9c1d3f5"
down_revision: str | None = "d4f6a8b0c2e4"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

RECOVERY_SESSION_TABLE_NAME = "recovery_session"


def upgrade() -> None:
    """Creates the recovery_session table with a row for each execution of the recovery agent."""
    op.create_table(
        RECOVERY_SESSION_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_token", sa.String(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("node_ids", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drops the recovery_session table."""
    op.drop_table(RECOVERY_SESSION_TABLE_NAME)

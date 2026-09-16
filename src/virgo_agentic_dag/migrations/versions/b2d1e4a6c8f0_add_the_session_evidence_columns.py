"""Adds evidence columns to agent sessions."""

import sqlalchemy as sa
from alembic import op

revision: str = "b2d1e4a6c8f0"
down_revision: str | None = "a1c0d3f5e7b9"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

AGENT_SESSIONS_TABLE_NAME = "agent_sessions"
EXIT_CODE_COLUMN_NAME = "exit_code"
LOG_TAIL_COLUMN_NAME = "log_tail"
MARKS_BEFORE_COLUMN_NAME = "marks_before"


def upgrade() -> None:
    """Adds the three nullable evidence columns to agent sessions."""
    op.add_column(
        AGENT_SESSIONS_TABLE_NAME,
        sa.Column(EXIT_CODE_COLUMN_NAME, sa.Integer(), nullable=True),
    )
    op.add_column(
        AGENT_SESSIONS_TABLE_NAME,
        sa.Column(LOG_TAIL_COLUMN_NAME, sa.String(), nullable=True),
    )
    op.add_column(
        AGENT_SESSIONS_TABLE_NAME,
        sa.Column(MARKS_BEFORE_COLUMN_NAME, sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drops the three evidence columns from agent sessions."""
    op.drop_column(AGENT_SESSIONS_TABLE_NAME, MARKS_BEFORE_COLUMN_NAME)
    op.drop_column(AGENT_SESSIONS_TABLE_NAME, LOG_TAIL_COLUMN_NAME)
    op.drop_column(AGENT_SESSIONS_TABLE_NAME, EXIT_CODE_COLUMN_NAME)

"""Creates the node_recovery table."""

import sqlalchemy as sa
from alembic import op

revision: str = "c3e5a7b9d1f2"
down_revision: str | None = "b2d1e4a6c8f0"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

NODE_RECOVERY_TABLE_NAME = "node_recovery"
NODE_RECOVERY_NODE_ID_INDEX_NAME = "ix_node_recovery_node_id"


def upgrade() -> None:
    """Creates the node_recovery table with a row for each failure of a node."""
    op.create_table(
        NODE_RECOVERY_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cause", sa.String(), nullable=False),
        sa.Column("recoverable", sa.Boolean(), nullable=False),
        sa.Column("recover_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        NODE_RECOVERY_NODE_ID_INDEX_NAME,
        NODE_RECOVERY_TABLE_NAME,
        ["node_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drops the node_recovery table."""
    op.drop_index(NODE_RECOVERY_NODE_ID_INDEX_NAME, table_name=NODE_RECOVERY_TABLE_NAME)
    op.drop_table(NODE_RECOVERY_TABLE_NAME)

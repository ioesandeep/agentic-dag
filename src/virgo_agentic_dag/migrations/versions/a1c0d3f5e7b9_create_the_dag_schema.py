"""Creates the eight tables of a dag database."""

import sqlalchemy as sa
from alembic import op

revision: str = "a1c0d3f5e7b9"
down_revision: str | None = None
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

AUDIT_ENTRIES_TABLE_NAME = "audit_entries"
NODES_TABLE_NAME = "nodes"
SCHEDULED_JOBS_TABLE_NAME = "scheduled_jobs"
SLACK_NOTIFICATIONS_TABLE_NAME = "slack_notifications"
WATCHERS_TABLE_NAME = "watchers"
NODE_AGENTS_TABLE_NAME = "node_agents"
AGENT_SESSIONS_TABLE_NAME = "agent_sessions"
WORK_TREES_TABLE_NAME = "work_trees"
AUDIT_ENTRIES_NODE_ID_INDEX_NAME = "ix_audit_entries_node_id"
SLACK_NOTIFICATIONS_NODE_ID_INDEX_NAME = "ix_slack_notifications_node_id"


def upgrade() -> None:
    """Creates the eight tables of a dag database."""
    op.create_table(
        AUDIT_ENTRIES_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        AUDIT_ENTRIES_NODE_ID_INDEX_NAME,
        AUDIT_ENTRIES_TABLE_NAME,
        ["node_id"],
        unique=False,
    )

    op.create_table(
        NODES_TABLE_NAME,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        SCHEDULED_JOBS_TABLE_NAME,
        sa.Column("dag_name", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("argv", sa.String(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("working_directory", sa.String(), nullable=False),
        sa.Column("log_path", sa.String(), nullable=False),
        sa.Column("environment", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dag_name"),
    )

    op.create_table(
        SLACK_NOTIFICATIONS_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        SLACK_NOTIFICATIONS_NODE_ID_INDEX_NAME,
        SLACK_NOTIFICATIONS_TABLE_NAME,
        ["node_id"],
        unique=True,
    )

    op.create_table(
        WATCHERS_TABLE_NAME,
        sa.Column("dag_name", sa.String(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dag_name"),
    )

    op.create_table(
        NODE_AGENTS_TABLE_NAME,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("resume_token", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        AGENT_SESSIONS_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_state", sa.String(), nullable=False),
        sa.Column("triggered_by", sa.String(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("pid_start", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["node_agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        WORK_TREES_TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("absolute_path", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("marks", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reclaimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["node_agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )


def downgrade() -> None:
    """Drops the eight tables of a dag database."""
    op.drop_table(WORK_TREES_TABLE_NAME)
    op.drop_table(AGENT_SESSIONS_TABLE_NAME)
    op.drop_table(NODE_AGENTS_TABLE_NAME)
    op.drop_table(WATCHERS_TABLE_NAME)
    op.drop_index(
        SLACK_NOTIFICATIONS_NODE_ID_INDEX_NAME,
        table_name=SLACK_NOTIFICATIONS_TABLE_NAME,
    )
    op.drop_table(SLACK_NOTIFICATIONS_TABLE_NAME)
    op.drop_table(SCHEDULED_JOBS_TABLE_NAME)
    op.drop_table(NODES_TABLE_NAME)
    op.drop_index(AUDIT_ENTRIES_NODE_ID_INDEX_NAME, table_name=AUDIT_ENTRIES_TABLE_NAME)
    op.drop_table(AUDIT_ENTRIES_TABLE_NAME)

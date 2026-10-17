"""Create catalog project storage."""

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Integer, Text, text
from sqlalchemy.schema import SchemaItem

revision: str = "c001"
down_revision: str | None = None
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Create project storage with unique names and a single default."""
    timestamp_type = DateTime(timezone=True)
    empty_description = text("''")
    project_columns: list[SchemaItem] = [
        Column("id", Text, primary_key=True, nullable=False),
        Column("name", Text, nullable=False),
        Column("name_key", Text, nullable=False, unique=True),
        Column("description", Text, nullable=False, server_default=empty_description),
        Column("is_default", Boolean, nullable=False, server_default="0"),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", timestamp_type, nullable=False),
        Column("updated_at", timestamp_type, nullable=False),
        Column("archived_at", timestamp_type, nullable=True),
    ]
    op.create_table("projects", *project_columns)

    default_predicate = text("is_default = 1")
    op.create_index(
        "uq_projects_is_default",
        "projects",
        ["is_default"],
        unique=True,
        sqlite_where=default_predicate,
    )


def downgrade() -> None:
    """Remove catalog project storage."""
    op.drop_index("uq_projects_is_default", table_name="projects")
    op.drop_table("projects")

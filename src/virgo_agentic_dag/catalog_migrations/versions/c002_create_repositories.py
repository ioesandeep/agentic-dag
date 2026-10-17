"""Create catalog repository storage."""

from alembic import op
from sqlalchemy import Column, DateTime, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.schema import SchemaItem

revision: str = "c002"
down_revision: str | None = "c001"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Create repository storage with unique identities and checkout paths."""
    provider_type = Enum(
        "github", native_enum=False, create_constraint=True, name="repository_provider"
    )
    checkout_kind_type = Enum(
        "managed",
        "external",
        native_enum=False,
        create_constraint=True,
        name="repository_checkout_kind",
    )
    checkout_state_type = Enum(
        "pending",
        "ready",
        "missing",
        "invalid",
        native_enum=False,
        create_constraint=True,
        name="repository_checkout_state",
    )
    timestamp_type = DateTime(timezone=True)
    repository_columns: list[SchemaItem] = [
        Column("id", Text, primary_key=True, nullable=False),
        Column("provider", provider_type, nullable=False),
        Column("host", Text, nullable=False),
        Column("provider_repository_id", Text, nullable=False),
        Column("full_name", Text, nullable=False),
        Column("web_url", Text, nullable=False),
        Column("default_branch", Text, nullable=True),
        Column("checkout_kind", checkout_kind_type, nullable=False),
        Column("checkout_path", Text, nullable=False, unique=True),
        Column("remote_name", Text, nullable=False),
        Column("checkout_state", checkout_state_type, nullable=False),
        Column("last_checked_at", timestamp_type, nullable=True),
        Column("validation_message", Text, nullable=True),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", timestamp_type, nullable=False),
        Column("updated_at", timestamp_type, nullable=False),
        Column("archived_at", timestamp_type, nullable=True),
        UniqueConstraint(
            "provider",
            "host",
            "provider_repository_id",
            name="uq_repositories_identity",
        ),
    ]
    op.create_table("repositories", *repository_columns)


def downgrade() -> None:
    """Remove catalog repository storage."""
    op.drop_table("repositories")

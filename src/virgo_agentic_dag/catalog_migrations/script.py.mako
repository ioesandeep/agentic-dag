"""${message}"""

from alembic import op

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | list[str] | None = ${repr(branch_labels)}
depends_on: str | list[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply the catalog schema revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert the catalog schema revision."""
    ${downgrades if downgrades else "pass"}

from alembic import context

from virgo_agentic_dag.domain.catalog.entities.project import Project as Project
from virgo_agentic_dag.domain.catalog.entities.repository import Repository

config = context.config
connection = config.attributes["connection"]
context.configure(connection=connection, target_metadata=Repository.metadata)

with context.begin_transaction():
    context.run_migrations()

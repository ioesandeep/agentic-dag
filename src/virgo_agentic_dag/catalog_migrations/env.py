from alembic import context

from virgo_agentic_dag.domain.catalog.entities.project import Project

config = context.config
connection = config.attributes["connection"]
context.configure(connection=connection, target_metadata=Project.metadata)

with context.begin_transaction():
    context.run_migrations()

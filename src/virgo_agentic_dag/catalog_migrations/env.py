from alembic import context

from virgo_agentic_dag.domain.catalog.entities.catalog_entity_base import (
    CatalogEntityBase,
)

config = context.config
connection = config.attributes["connection"]
context.configure(connection=connection, target_metadata=CatalogEntityBase.metadata)

with context.begin_transaction():
    context.run_migrations()

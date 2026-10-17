from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from virgo_agentic_dag.domain.catalog.entities.catalog_entity_base import (
    CatalogEntityBase,
)


class Project(CatalogEntityBase):
    """Persist project metadata independently of DAG runs."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    _empty_description = text("''")
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=_empty_description
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    _timestamp_type = DateTime(timezone=True)
    created_at: Mapped[datetime] = mapped_column(_timestamp_type, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(_timestamp_type, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(_timestamp_type, nullable=True)

    _default_predicate = text("is_default = 1")
    _default_index = Index(
        "uq_projects_is_default",
        "is_default",
        unique=True,
        sqlite_where=_default_predicate,
    )
    __table_args__ = (_default_index,)

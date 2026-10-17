from dataclasses import dataclass
from typing import Protocol

from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)


class CatalogConflictRecord(Protocol):
    """Identify the catalog record for a version conflict."""

    id: str
    version: int


@dataclass(kw_only=True)
class CatalogError(Exception):
    """Describe a catalog failure with typed context."""

    code: CatalogErrorCodeEnum
    detail: str
    field: str | None = None
    existing_project_id: str | None = None
    existing_repository_id: str | None = None
    project_ids: list[str] | None = None
    import_id: str | None = None
    current: CatalogConflictRecord | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.detail)

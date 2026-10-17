import os
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.utils.dag_utils import get_dag_root


def _get_catalog_root() -> Path:
    environment_root = os.getenv("VIRGO_DAG_CATALOG_ROOT")
    if environment_root is None:
        return get_dag_root()

    catalog_root = Path(environment_root)

    return catalog_root.expanduser()


@dataclass(frozen=True)
class CatalogSettings:
    """Configure catalog storage independently of DAG runs."""

    root: Path = field(default_factory=_get_catalog_root)

    @property
    def db_path(self) -> Path:
        """Locate catalog metadata."""
        return self.root / "db.sqlite"

    @property
    def repositories_path(self) -> Path:
        """Locate managed checkouts."""
        return self.root / "repositories"

    @property
    def imports_path(self) -> Path:
        """Locate import staging directories."""
        return self.repositories_path / ".imports"

    @property
    def locks_path(self) -> Path:
        """Locate catalog initialization and import locks."""
        return self.root / ".locks" / "catalog"

    def get_repository_path(self, repository_id: str) -> Path:
        """Locate a managed checkout by repository ID."""
        catalog_id = self._parse_catalog_id(repository_id, "repository_id")

        return self.repositories_path / catalog_id

    def get_import_path(self, import_id: str) -> Path:
        """Locate a staging directory by import ID."""
        catalog_id = self._parse_catalog_id(import_id, "import_id")

        return self.imports_path / catalog_id

    @staticmethod
    def _parse_catalog_id(catalog_id: str, field: str) -> str:
        try:
            identifier = UUID(catalog_id)
        except ValueError as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.INVALID_INPUT,
                detail="Catalog identifiers must be UUIDs.",
                field=field,
            ) from error

        return str(identifier)

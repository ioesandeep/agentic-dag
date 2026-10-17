import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.utils.dag_utils import get_dag_db_path

pytestmark = pytest.mark.unit


def test_catalog_uses_the_dag_root_when_no_override_exists(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.dict(os.environ, {}, clear=True)
    mocker.patch.object(Path, "home", return_value=tmp_path)

    catalog_settings = CatalogSettings()

    assert catalog_settings.db_path == tmp_path / ".virgo-dag" / "db.sqlite"


def test_catalog_override_preserves_run_paths(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    catalog_root = tmp_path / "catalog"
    environment_root = str(catalog_root)
    mocker.patch.object(Path, "home", return_value=tmp_path)
    mocker.patch.dict(os.environ, {"VIRGO_DAG_CATALOG_ROOT": environment_root})

    catalog_settings = CatalogSettings()
    run_db_path = get_dag_db_path("demo")

    assert catalog_settings.db_path == tmp_path / "catalog" / "db.sqlite"
    assert run_db_path == tmp_path / ".virgo-dag" / "demo" / "db.sqlite3"


def test_injected_catalog_root_overrides_the_environment_without_creating_files(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.dict(os.environ, {"VIRGO_DAG_CATALOG_ROOT": "/unused"})
    catalog_root = tmp_path / "catalog"

    catalog_settings = CatalogSettings(root=catalog_root)
    catalog_root_exists = catalog_root.exists()

    assert catalog_settings.db_path == catalog_root / "db.sqlite"
    assert catalog_settings.repositories_path == catalog_root / "repositories"
    assert catalog_settings.imports_path == catalog_root / "repositories" / ".imports"
    assert catalog_settings.locks_path == catalog_root / ".locks" / "catalog"
    assert not catalog_root_exists


def test_catalog_derives_checkout_and_staging_paths_from_uuid_identifiers(
    tmp_path: Path,
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    catalog_id = "550E8400-E29B-41D4-A716-446655440000"
    expected_catalog_id = catalog_id.lower()

    repository_path = catalog_settings.get_repository_path(catalog_id)
    import_path = catalog_settings.get_import_path(catalog_id)

    assert repository_path == tmp_path / "repositories" / expected_catalog_id
    assert import_path == tmp_path / "repositories" / ".imports" / expected_catalog_id


@pytest.mark.parametrize("catalog_id", ["../outside", "/outside", ""])
def test_catalog_rejects_malformed_identifiers_before_constructing_paths(
    tmp_path: Path, catalog_id: str
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)

    with pytest.raises(CatalogError, match="must be UUIDs") as repository_error:
        catalog_settings.get_repository_path(catalog_id)

    with pytest.raises(CatalogError, match="must be UUIDs") as import_error:
        catalog_settings.get_import_path(catalog_id)

    assert repository_error.value.code is CatalogErrorCodeEnum.INVALID_INPUT
    assert repository_error.value.field == "repository_id"
    assert import_error.value.field == "import_id"

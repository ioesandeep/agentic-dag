from collections.abc import Callable
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.checkout_kind_enum import CheckoutKindEnum
from virgo_agentic_dag.domain.catalog.checkout_state_enum import CheckoutStateEnum
from virgo_agentic_dag.domain.catalog.entities.repository import Repository
from virgo_agentic_dag.domain.catalog.repository_provider_enum import (
    RepositoryProviderEnum,
)
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.catalog.catalog_database import CatalogDatabase

pytestmark = pytest.mark.integration


@pytest.fixture
def create_repository() -> Callable[[int, str], Repository]:
    current_time = datetime(2026, 10, 17, tzinfo=UTC)

    return lambda identifier, checkout_path: Repository(
        id=f"00000000-0000-0000-0000-{identifier:012d}",
        provider=RepositoryProviderEnum.GITHUB,
        host="github.com",
        provider_repository_id=f"{identifier}",
        full_name="acme/virgo",
        web_url="https://github.com/acme/virgo",
        checkout_kind=CheckoutKindEnum.EXTERNAL,
        checkout_path=checkout_path,
        remote_name="origin",
        checkout_state=CheckoutStateEnum.READY,
        created_at=current_time,
        updated_at=current_time,
    )


async def test_repositories_persist_renamed_metadata_when_default_branch_is_absent(
    tmp_path: Path, create_repository: Callable[[int, str], Repository]
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    repository = create_repository(1, f"{tmp_path}/checkout")

    async with database.session() as session:
        session.add(repository)
        await session.commit()
        repository.full_name = "acme/renamed"
        repository.web_url = "https://github.com/acme/renamed"
        await session.commit()

    async with database.session() as session:
        persisted_repository = await session.get(Repository, repository.id)

    await database.dispose()

    assert persisted_repository is not None
    assert persisted_repository.full_name == "acme/renamed"
    assert persisted_repository.provider_repository_id == "1"
    assert persisted_repository.default_branch is None
    assert persisted_repository.provider is RepositoryProviderEnum.GITHUB
    assert persisted_repository.checkout_kind is CheckoutKindEnum.EXTERNAL
    assert persisted_repository.checkout_state is CheckoutStateEnum.READY
    assert persisted_repository.version == 1


@pytest.mark.parametrize(
    ("is_duplicate_path", "constraint_columns"),
    [
        (False, "provider, repositories.host, repositories.provider_repository_id"),
        (True, "checkout_path"),
    ],
    ids=["renamed-github-identity", "canonical-checkout-path"],
)
async def test_repositories_reject_duplicate_registration_keys(
    tmp_path: Path,
    create_repository: Callable[[int, str], Repository],
    is_duplicate_path: bool,
    constraint_columns: str,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    repository = create_repository(1, f"{tmp_path}/checkout")
    duplicate_repository = create_repository(2, f"{tmp_path}/another-checkout")
    duplicate_repository.full_name = "acme/renamed"
    if is_duplicate_path:
        duplicate_repository.checkout_path = repository.checkout_path
    else:
        duplicate_repository.provider_repository_id = repository.provider_repository_id

    constraint_error = f"UNIQUE constraint failed: repositories.{constraint_columns}"

    async with database.session() as session:
        session.add(repository)
        await session.commit()
        session.add(duplicate_repository)
        with pytest.raises(IntegrityError, match=constraint_error):
            await session.commit()

    await database.dispose()


def test_repository_migration_matches_model_after_each_upgrade(tmp_path: Path) -> None:
    migrations_path = files("virgo_agentic_dag") / "catalog_migrations"
    script_location = str(migrations_path)
    config = Config()
    config.set_main_option("script_location", script_location)
    engine = create_engine(f"sqlite:///{tmp_path}/db.sqlite")

    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            for _ in range(2):
                command.upgrade(config, "c002")
                migration_context = MigrationContext.configure(
                    connection, opts={"compare_server_default": True}
                )
                schema_differences = compare_metadata(
                    migration_context, Repository.metadata
                )
                assert schema_differences == []
                command.downgrade(config, "c001")
                catalog_inspector = inspect(connection)
                catalog_tables = catalog_inspector.get_table_names()
                assert catalog_tables == ["alembic_version", "projects"]
    finally:
        engine.dispose()

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
from virgo_agentic_dag.domain.catalog.entities.project import Project
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.catalog.catalog_database import CatalogDatabase

pytestmark = pytest.mark.integration


@pytest.fixture
def create_project() -> Callable[[str, str], Project]:
    current_time = datetime(2026, 10, 17, tzinfo=UTC)

    return lambda project_id, name_key: Project(
        id=project_id,
        name=name_key,
        name_key=name_key,
        created_at=current_time,
        updated_at=current_time,
    )


async def test_projects_persist_defaults_when_optional_values_are_omitted(
    tmp_path: Path, create_project: Callable[[str, str], Project]
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    project = create_project("00000000-0000-0000-0000-000000000001", "virgo")
    another_project = create_project("00000000-0000-0000-0000-000000000002", "docs")

    async with database.session() as session:
        session.add_all([project, another_project])
        await session.commit()

    async with database.session() as session:
        persisted_project = await session.get(Project, project.id)

    await database.dispose()

    assert persisted_project is not None
    assert persisted_project.description == ""
    assert persisted_project.version == 1
    assert persisted_project.is_default is False
    assert persisted_project.archived_at is None
    created_at = persisted_project.created_at.replace(tzinfo=UTC)
    updated_at = persisted_project.updated_at.replace(tzinfo=UTC)
    assert created_at == project.created_at
    assert updated_at == project.updated_at


@pytest.mark.parametrize(
    ("is_default", "is_archived"),
    [(False, False), (False, True), (True, False)],
    ids=["active-name", "archived-name", "default-project"],
)
async def test_projects_reject_duplicate_catalog_keys(
    tmp_path: Path,
    create_project: Callable[[str, str], Project],
    is_default: bool,
    is_archived: bool,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    name_key = "virgo" if not is_default else "default"
    first_project = create_project("00000000-0000-0000-0000-000000000001", name_key)
    first_project.name = " Virgo " if not is_default else "Default"
    first_project.is_default = is_default
    first_project.archived_at = first_project.created_at if is_archived else None
    duplicate_key = "another-default" if is_default else "virgo"
    duplicate_project = create_project(
        "00000000-0000-0000-0000-000000000002", duplicate_key
    )
    duplicate_project.is_default = is_default
    column_name = "is_default" if is_default else "name_key"
    constraint_error = f"UNIQUE constraint failed: projects.{column_name}"

    async with database.session() as session:
        session.add(first_project)
        await session.commit()
        session.add(duplicate_project)
        with pytest.raises(IntegrityError, match=constraint_error):
            await session.commit()

    await database.dispose()


def test_project_migration_matches_model_after_each_upgrade(tmp_path: Path) -> None:
    migrations_path = files("virgo_agentic_dag") / "catalog_migrations"
    script_location = str(migrations_path)
    config = Config()
    config.set_main_option("script_location", script_location)
    engine = create_engine(f"sqlite:///{tmp_path}/db.sqlite")

    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            for _ in range(2):
                command.upgrade(config, "c001")
                migration_context = MigrationContext.configure(
                    connection, opts={"compare_server_default": True}
                )
                schema_differences = compare_metadata(
                    migration_context, Project.metadata
                )
                assert schema_differences == []
                command.downgrade(config, "base")
                catalog_inspector = inspect(connection)
                catalog_tables = catalog_inspector.get_table_names()
                assert catalog_tables == ["alembic_version"]
    finally:
        engine.dispose()

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.entities.project import Project
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.catalog.catalog_database import CatalogDatabase
from virgo_agentic_dag.infra.persistence.catalog.project_store import ProjectStore

pytestmark = pytest.mark.integration


@pytest.fixture
def create_project() -> Callable[[int, str], Project]:
    current_time = datetime(2026, 10, 17, tzinfo=UTC)

    return lambda project_number, name: Project(
        id=f"00000000-0000-0000-0000-{project_number:012d}",
        name=name,
        name_key=name,
        description="",
        created_at=current_time,
        updated_at=current_time,
    )


@pytest.mark.parametrize("should_commit", [False, True])
async def test_ensure_default_respects_caller_transactions_across_concurrent_sessions(
    tmp_path: Path,
    should_commit: bool,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    current_time = datetime(2026, 10, 17, tzinfo=UTC)

    async def initialize_default() -> str:
        async with database.session() as session:
            project_store = ProjectStore(session=session)
            project = await project_store.ensure_default(current_time)
            repeated_project = await project_store.ensure_default(current_time)
            assert project.id == repeated_project.id
            if should_commit:
                await session.commit()

            return project.id

    initializations = [initialize_default() for _ in range(4)]
    project_ids = await asyncio.gather(*initializations)

    async with database.session() as session:
        project_store = ProjectStore(session=session)
        projects = await project_store.list(include_archived=True)

    await database.dispose()
    if should_commit:
        distinct_project_ids = set(project_ids)
        assert len(distinct_project_ids) == 1
        assert len(projects) == 1
        assert projects[0].name == "Default"
    else:
        assert projects == []


async def test_list_sorts_default_first_and_excludes_archived_projects_by_default(
    tmp_path: Path,
    create_project: Callable[[int, str], Project],
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    alpha = create_project(1, "alpha")
    zeta = create_project(2, "zeta")
    zeta.name = "ZETA"
    alpha.archived_at = alpha.updated_at

    async with database.session() as session:
        project_store = ProjectStore(session=session)
        await project_store.create(zeta)
        await project_store.create(alpha)
        await project_store.ensure_default(alpha.created_at)
        await session.commit()

    async with database.session() as session:
        project_store = ProjectStore(session=session)
        active_projects = await project_store.list()
        all_projects = await project_store.list(include_archived=True)

    await database.dispose()
    assert [project.name for project in active_projects] == ["Default", "ZETA"]
    assert [project.name for project in all_projects] == ["Default", "alpha", "ZETA"]


@pytest.mark.parametrize(
    ("is_archived", "is_default"), [(False, False), (True, False), (False, True)]
)
async def test_project_writes_reject_a_name_used_by_another_project(
    tmp_path: Path,
    create_project: Callable[[int, str], Project],
    is_archived: bool,
    is_default: bool,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    project_name = "default" if is_default else "virgo"
    project = create_project(1, project_name)
    project.archived_at = project.updated_at if is_archived else None
    duplicate_project = create_project(2, project_name)
    duplicate_project.name_key = project.name_key

    async with database.session() as session:
        project_store = ProjectStore(session=session)
        await project_store.create(project)
        await session.commit()

    async with database.session() as session:
        project_store = ProjectStore(session=session)
        with pytest.raises(IntegrityError, match="projects.name_key"):
            if is_default:
                await project_store.ensure_default(project.created_at)
            else:
                await project_store.create(duplicate_project)

    await database.dispose()


@pytest.mark.parametrize("is_archive_change", [False, True])
async def test_project_mutations_preserve_current_values_when_the_version_is_stale(
    tmp_path: Path,
    create_project: Callable[[int, str], Project],
    is_archive_change: bool,
) -> None:
    settings = CatalogSettings(root=tmp_path)
    migration_lock = DagRunLock(settings.locks_path / "migrations")
    database = CatalogDatabase(catalog_settings=settings, migration_lock=migration_lock)
    await database.initialize()
    project = create_project(1, "virgo")
    async with database.session() as session:
        project_store = ProjectStore(session=session)
        await project_store.create(project)
        await session.commit()

    async with database.session() as stale_session, database.session() as session:
        stale_project_store = ProjectStore(session=stale_session)
        stale_project = await stale_project_store.get(project.id)
        assert stale_project is not None
        project_store = ProjectStore(session=session)
        project.description = "Current description"
        project.archived_at = project.updated_at
        if is_archive_change:
            project_update_result = await project_store.set_archived(
                project, expected_version=1
            )
        else:
            project_update_result = await project_store.update(
                project, expected_version=1
            )

        await session.commit()
        stale_project.name = "stale"
        stale_project.description = "Stale description"
        stale_project.archived_at = None
        if is_archive_change:
            stale_project_update_result = await stale_project_store.set_archived(
                stale_project, expected_version=1
            )
        else:
            stale_project_update_result = await stale_project_store.update(
                stale_project, expected_version=1
            )

        await stale_session.commit()

    await database.dispose()
    assert project_update_result.is_updated is True
    assert stale_project_update_result.is_updated is False
    assert stale_project_update_result.project.version == 2
    assert stale_project_update_result.project.name == "virgo"
    if is_archive_change:
        assert stale_project_update_result.project.archived_at is not None
        assert stale_project_update_result.project.description == ""
    else:
        assert stale_project_update_result.project.archived_at is None
        assert stale_project_update_result.project.description == "Current description"

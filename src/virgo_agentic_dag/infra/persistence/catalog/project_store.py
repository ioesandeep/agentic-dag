from datetime import datetime
from uuid import uuid4

from sqlalchemy import Update, select, text, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.entities.project import Project
from virgo_agentic_dag.domain.catalog.ports.project_store import (
    ProjectStore as ProjectStorePort,
)
from virgo_agentic_dag.domain.catalog.project_update_result import ProjectUpdateResult


class ProjectStore(ProjectStorePort):
    """Persist projects without committing the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, project_id: str) -> Project | None:
        """Return the current project for an identifier."""
        statement = select(Project).where(Project.id == project_id)
        statement = statement.execution_options(populate_existing=True, autoflush=False)
        projects = await self._session.execute(statement)

        return projects.scalar_one_or_none()

    async def list(self, include_archived: bool = False) -> list[Project]:
        """Return projects with Default first and normalized names in order."""
        default_order = Project.is_default.desc()
        statement = select(Project).order_by(default_order, Project.name_key)
        if not include_archived:
            active_predicate = Project.archived_at.is_(None)
            statement = statement.where(active_predicate)

        projects = await self._session.scalars(statement)

        return list(projects)

    async def create(self, project: Project) -> Project:
        """Persist a new project."""
        self._session.add(project)
        await self._session.flush()

        return project

    async def ensure_default(self, current_time: datetime) -> Project:
        """Return the protected initial project."""
        project_uuid = uuid4()
        project_id = str(project_uuid)
        statement = insert(Project).values(
            id=project_id,
            name="Default",
            name_key="default",
            is_default=True,
            created_at=current_time,
            updated_at=current_time,
        )
        default_predicate = text("is_default = 1")
        statement = statement.on_conflict_do_nothing(
            index_elements=[Project.is_default], index_where=default_predicate
        )
        await self._session.execute(statement)
        is_default_predicate = Project.is_default.is_(True)
        default_statement = select(Project).where(is_default_predicate)
        projects = await self._session.scalars(default_statement)

        return projects.one()

    async def update(
        self, project: Project, expected_version: int
    ) -> ProjectUpdateResult:
        """Update project metadata when its version matches."""
        statement = (
            update(Project)
            .where(Project.id == project.id, Project.version == expected_version)
            .values(
                name=project.name,
                name_key=project.name_key,
                description=project.description,
                updated_at=project.updated_at,
                version=Project.version + 1,
            )
        )

        return await self._update(statement, project.id)

    async def set_archived(
        self, project: Project, expected_version: int
    ) -> ProjectUpdateResult:
        """Update project archive state when its version matches."""
        statement = (
            update(Project)
            .where(Project.id == project.id, Project.version == expected_version)
            .values(
                archived_at=project.archived_at,
                updated_at=project.updated_at,
                version=Project.version + 1,
            )
        )

        return await self._update(statement, project.id)

    async def _update(self, statement: Update, project_id: str) -> ProjectUpdateResult:
        versioned_statement = statement.returning(Project.id).execution_options(
            autoflush=False, synchronize_session=False
        )
        updated_projects = await self._session.execute(versioned_statement)
        updated_project_id = updated_projects.scalar_one_or_none()
        project = await self.get(project_id)
        if project is None:
            raise CatalogError(
                code=CatalogErrorCodeEnum.PROJECT_NOT_FOUND,
                detail="Project does not exist.",
            )

        return ProjectUpdateResult(
            project=project, is_updated=updated_project_id is not None
        )

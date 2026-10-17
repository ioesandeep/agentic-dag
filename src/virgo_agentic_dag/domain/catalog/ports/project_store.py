from abc import ABC, abstractmethod
from datetime import datetime

from virgo_agentic_dag.domain.catalog.entities.project import Project
from virgo_agentic_dag.domain.catalog.project_update_result import ProjectUpdateResult


class ProjectStore(ABC):
    """Define project persistence within a caller's transaction."""

    @abstractmethod
    async def get(self, project_id: str) -> Project | None:
        """Return the current project for an identifier."""

    @abstractmethod
    async def list(self, include_archived: bool = False) -> list[Project]:
        """Return projects with Default first and normalized names in order."""

    @abstractmethod
    async def create(self, project: Project) -> Project:
        """Persist a new project."""

    @abstractmethod
    async def ensure_default(self, current_time: datetime) -> Project:
        """Return the protected initial project."""

    @abstractmethod
    async def update(
        self, project: Project, expected_version: int
    ) -> ProjectUpdateResult:
        """Update project metadata when its version matches."""

    @abstractmethod
    async def set_archived(
        self, project: Project, expected_version: int
    ) -> ProjectUpdateResult:
        """Update project archive state when its version matches."""

from dataclasses import dataclass

from virgo_agentic_dag.domain.catalog.entities.project import Project


@dataclass(frozen=True, kw_only=True)
class ProjectUpdateResult:
    """Report whether a versioned project mutation succeeds."""

    project: Project
    is_updated: bool

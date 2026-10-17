from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.catalog.github_auth_status import GithubAuthStatus


class GithubAuthStatusClient(ABC):
    """Identify the GitHub account available to catalog services."""

    @abstractmethod
    async def status(self) -> GithubAuthStatus:
        """Check authentication for catalog operations."""

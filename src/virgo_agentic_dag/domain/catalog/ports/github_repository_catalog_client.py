from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.catalog.github_repository_identity import (
    GitHubRepositoryIdentity,
)
from virgo_agentic_dag.domain.catalog.github_repository_reference import (
    GitHubRepositoryReference,
)


class GitHubRepositoryCatalogClient(ABC):
    """Resolve identities for explicitly requested GitHub repositories."""

    @abstractmethod
    async def get_repository_identity(
        self, github_repository_reference: GitHubRepositoryReference
    ) -> GitHubRepositoryIdentity:
        """Resolve the repository explicitly requested by the caller."""

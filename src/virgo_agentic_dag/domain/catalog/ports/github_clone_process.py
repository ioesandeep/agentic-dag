from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.catalog.ports.github_clone_handle import GithubCloneHandle


class GithubCloneProcess(ABC):
    """Start independently controlled repository clones."""

    @abstractmethod
    async def start(
        self, reference: str, staging_path: Path, lock_descriptor: int
    ) -> GithubCloneHandle:
        """Start a clone that retains the repository import lock."""

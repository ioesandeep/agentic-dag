"""The hosting-platform interface a run's pull requests are read through."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact


class CodeRepo(ABC):
    """Reads pull requests in domain terms, keeping the platform out of the core."""

    @abstractmethod
    async def find_pull_request(self, graph_node: GraphNode, branch: str) -> int:
        """Return the number of the newest pull request opened from this branch, or 0."""

    @abstractmethod
    async def get_pull_request(
        self, graph_node: GraphNode, number: int
    ) -> PullRequestSnapshot:
        """Return this pull request's current state in one read."""

    @abstractmethod
    async def get_review_artifacts(
        self, graph_node: GraphNode, number: int
    ) -> list[ReviewArtifact]:
        """Return every comment and review left on this pull request."""

    @abstractmethod
    async def count_commits_between(
        self, graph_node: GraphNode, base_sha: str, head_sha: str
    ) -> int:
        """Return the number of commits between the base SHA and head SHA."""

    @abstractmethod
    async def get_repo_slug(self, project_root: Path) -> str:
        """Return the owner/repo name of the repository this checkout belongs to."""

    @abstractmethod
    async def get_repo_url(self, project_root: Path) -> str:
        """Return the web url of the repository this checkout belongs to."""

    @abstractmethod
    async def get_pr_details_from_url(self, pr_url: str) -> PullRequestDetails:
        """Return the pull request's number, repository, and head branch, from its url alone."""

    @abstractmethod
    async def clone_repository(self, repository: str, destination: Path) -> None:
        """Clone this repository into the destination directory."""

"""The CodeRepo adapter backed by the gh CLI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.infra.code.pull_request_snapshot_mapper import (
    REQUIRED_FIELDS,
    PullRequestSnapshotMapper,
)
from virgo_agentic_dag.infra.code.review_artifact_mapper import ReviewArtifactMapper
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

_ENDPOINTS: tuple[tuple[ReviewArtifactType, str], ...] = (
    (ReviewArtifactType.ISSUE_COMMENT, "repos/{owner}/{repo}/issues/%s/comments"),
    (ReviewArtifactType.REVIEW_COMMENT, "repos/{owner}/{repo}/pulls/%s/comments"),
    (ReviewArtifactType.REVIEW, "repos/{owner}/{repo}/pulls/%s/reviews"),
)


class GitHubCodeRepo(CodeRepo):
    """Runs every gh call inside the node's project root, so gh resolves the repository itself."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def find_pull_request(self, graph_node: GraphNode, branch: str) -> int:
        argv = (
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            "number",
            "--limit",
            "100",
        )

        result = await self._run(graph_node, argv)
        if result.returncode != 0:
            raise ObservationError(f"gh pr list for {branch} failed")

        return self._get_newest(result.stdout, branch)

    async def get_pull_request(
        self, graph_node: GraphNode, number: int
    ) -> PullRequestSnapshot:
        fields = ",".join((*REQUIRED_FIELDS, "mergeCommit", "mergedBy", "title", "url"))
        argv = ("gh", "pr", "view", str(number), "--json", fields)

        result = await self._run(graph_node, argv)
        if result.returncode != 0:
            raise ObservationError(f"gh pr view {number} failed")

        payload = self._parse_object(result.stdout, number)
        snapshot_mapper = PullRequestSnapshotMapper()

        return snapshot_mapper.get_snapshot(payload)

    async def get_review_artifacts(
        self, graph_node: GraphNode, number: int
    ) -> list[ReviewArtifact]:
        artifact_mapper = ReviewArtifactMapper()

        artifacts: list[ReviewArtifact] = []
        for kind, path_template in _ENDPOINTS:
            entries = await self._get_entries(graph_node, path_template % number)
            artifacts.extend(artifact_mapper.get_all(kind, entries))

        return artifacts

    async def count_commits_between(
        self, graph_node: GraphNode, base_sha: str, head_sha: str
    ) -> int:
        path = f"repos/{{owner}}/{{repo}}/compare/{base_sha}...{head_sha}"
        argv = ("gh", "api", path)

        result = await self._run(graph_node, argv)
        if result.returncode != 0:
            raise ObservationError(f"gh api {path} failed")

        payload = self._parse_object(result.stdout, path)
        total_commits = payload.get("total_commits")
        if total_commits is None:
            raise ObservationError(f"gh api {path} returned no commit count")

        return int(total_commits)

    async def get_repo_slug(self, project_root: Path) -> str:
        argv = (
            "gh",
            "repo",
            "view",
            "--json",
            "nameWithOwner",
            "--jq",
            ".nameWithOwner",
        )

        result = await asyncio.to_thread(self._command_runner.run, argv, project_root)
        if result.returncode != 0:
            raise ObservationError(f"gh repo view failed in {project_root}")

        return result.stdout.strip()

    async def get_repo_url(self, project_root: Path) -> str:
        argv = ("gh", "repo", "view", "--json", "url", "--jq", ".url")

        result = await asyncio.to_thread(self._command_runner.run, argv, project_root)
        if result.returncode != 0:
            raise ObservationError(f"gh repo view --json url failed in {project_root}")

        return result.stdout.strip()

    async def get_pr_details_from_url(self, pr_url: str) -> PullRequestDetails:
        fields = "number,url,headRefName,headRepository,headRepositoryOwner,title"
        argv = ("gh", "pr", "view", pr_url, "--json", fields)

        result = await asyncio.to_thread(self._command_runner.run, argv)
        if result.returncode != 0:
            raise ObservationError(
                format_label(LABELS["prDetailsFailed"], {"pr": pr_url})
            )

        payload = self._parse_object(result.stdout, pr_url)
        number = int(payload.get("number") or 0)
        head_branch = str(payload.get("headRefName") or "")
        repository = self._get_repository(payload)
        if number == 0 or not head_branch or not repository:
            raise ObservationError(
                format_label(LABELS["prDetailsIncomplete"], {"pr": pr_url})
            )

        return PullRequestDetails(
            number=number,
            repository=repository,
            url=str(payload.get("url") or pr_url),
            head_branch=head_branch,
            title=str(payload.get("title") or ""),
        )

    def _get_repository(self, payload: dict[str, Any]) -> str:
        """Return owner/name of the repository the pull request's branch lives in."""
        owner = payload.get("headRepositoryOwner")
        repository = payload.get("headRepository")
        login = str(owner.get("login") or "") if isinstance(owner, dict) else ""
        name = str(repository.get("name") or "") if isinstance(repository, dict) else ""
        if not login or not name:
            return ""

        return f"{login}/{name}"

    async def clone_repository(self, repository: str, destination: Path) -> None:
        argv = ("gh", "repo", "clone", repository, str(destination))

        result = await asyncio.to_thread(
            self._command_runner.run, argv, destination.parent
        )
        if result.returncode != 0:
            raise ObservationError(
                format_label(
                    LABELS["cloneFailed"],
                    {"repository": repository, "destination": destination},
                )
            )

    async def _run(self, graph_node: GraphNode, argv: tuple[str, ...]) -> RunResult:
        return await asyncio.to_thread(
            self._command_runner.run, argv, graph_node.project_root
        )

    def _get_newest(self, payload: str, branch: str) -> int:
        try:
            entries = json.loads(payload or "[]")
        except json.JSONDecodeError as error:
            raise ObservationError(
                f"gh returned unreadable JSON for {branch}"
            ) from error

        numbers = [int(entry["number"]) for entry in entries if "number" in entry]
        if not numbers:
            return 0

        return max(numbers)

    def _parse_object(self, payload: str, subject: object) -> dict[str, Any]:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ObservationError(
                f"gh returned unreadable JSON for {subject}"
            ) from error

        if not isinstance(parsed, dict):
            raise ObservationError(f"gh returned a non-object payload for {subject}")

        return parsed

    async def _get_entries(
        self, graph_node: GraphNode, path: str
    ) -> list[dict[str, Any]]:
        argv = ("gh", "api", "--paginate", path)

        result = await self._run(graph_node, argv)
        if result.returncode != 0:
            raise ObservationError(f"gh api {path} failed")

        try:
            parsed = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as error:
            raise ObservationError(f"gh returned unreadable JSON for {path}") from error

        if not isinstance(parsed, list):
            raise ObservationError(f"gh returned a non-list payload for {path}")

        return parsed

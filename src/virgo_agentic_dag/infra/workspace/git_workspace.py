"""Workspace as git worktrees under one project root, one per node."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.host.base_branch_missing_error import (
    BaseBranchMissingError,
)
from virgo_agentic_dag.domain.exceptions.host.worktree_conflict_error import (
    WorktreeConflictError,
)
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree

REMOTE = "origin"


class GitWorkspace(Workspace):
    """Provisions and removes Git worktrees for graph nodes."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def provision(self, graph_node: GraphNode) -> WorkTree:
        path = graph_node.workspace_path / graph_node.id
        if path.exists():
            await self._validate_registered_worktree(graph_node.project_root, path)
        else:
            commit = await self._get_base_commit(graph_node)
            await self._add_worktree(graph_node.project_root, path, commit)

        return WorkTree(
            name=graph_node.id, absolute_path=str(path), created_at=datetime.now(UTC)
        )

    async def get_branch(self, worktree: WorkTree) -> str:
        result = await self._run_git(
            Path(worktree.absolute_path), ("branch", "--show-current")
        )

        if result.returncode != 0:
            raise WorktreeError(
                f"could not read the branch of {worktree.name}: {result.stderr.strip()}"
            )

        return result.stdout.strip()

    async def remove(self, worktree: WorkTree, project_root: Path) -> None:
        await self._prune(project_root)

        path = Path(worktree.absolute_path)
        if not path.exists():
            return

        remove_result = await self._run_git(
            project_root,
            ("worktree", "remove", "--force", worktree.absolute_path),
        )

        if remove_result.returncode != 0:
            raise WorktreeError(
                f"could not remove the worktree of {worktree.name}: "
                f"{remove_result.stderr.strip()}"
            )

    async def _validate_registered_worktree(
        self, project_root: Path, path: Path
    ) -> None:
        worktree_list_result = await self._run_git(
            project_root, ("worktree", "list", "--porcelain", "-z")
        )

        if worktree_list_result.returncode != 0:
            raise WorktreeError(
                f"could not list worktrees: {worktree_list_result.stderr.strip()}"
            )

        worktree_record = f"worktree {path.resolve()}"

        worktree_records = worktree_list_result.stdout.split("\0")
        if worktree_record not in worktree_records:
            raise WorktreeConflictError(
                f"{path} is not a registered worktree of {project_root}"
            )

    async def _get_base_commit(self, graph_node: GraphNode) -> str:
        project_root = graph_node.project_root
        base_branch = graph_node.base_branch
        fetch_result = await self._run_git(project_root, ("fetch", REMOTE, base_branch))

        base_ref = "FETCH_HEAD" if fetch_result.returncode == 0 else base_branch
        resolve_result = await self._run_git(
            project_root, ("rev-parse", "--verify", f"{base_ref}^{{commit}}")
        )

        if resolve_result.returncode != 0 and fetch_result.returncode != 0:
            fetch_result = await self._run_git(project_root, ("fetch", REMOTE))
            resolve_result = await self._run_git(
                project_root, ("rev-parse", "--verify", f"{base_branch}^{{commit}}")
            )

        if resolve_result.returncode == 0:
            return resolve_result.stdout.strip()

        if fetch_result.returncode != 0:
            raise WorktreeError(
                f"could not fetch {base_branch}: {fetch_result.stderr.strip()}"
            )

        raise BaseBranchMissingError(
            f"base branch {base_branch} does not resolve in {project_root}"
        )

    async def _add_worktree(self, project_root: Path, path: Path, commit: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        await self._prune(project_root)
        add_result = await self._run_git(
            project_root, ("worktree", "add", "--detach", str(path), commit)
        )

        if add_result.returncode != 0:
            raise WorktreeError(
                f"could not provision a worktree at {path}: {add_result.stderr.strip()}"
            )

    async def _prune(self, project_root: Path) -> None:
        prune_result = await self._run_git(project_root, ("worktree", "prune"))
        if prune_result.returncode != 0:
            raise WorktreeError(
                f"could not prune worktrees: {prune_result.stderr.strip()}"
            )

    async def _run_git(self, cwd: Path, argv: tuple[str, ...]) -> RunResult:
        return await asyncio.to_thread(
            self._command_runner.run, ("git", "-C", str(cwd), *argv)
        )

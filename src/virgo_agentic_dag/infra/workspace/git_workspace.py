"""Workspace as git worktrees under one project root, one per node."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree

REMOTE = "origin"


class GitWorkspace(Workspace):
    """Provisions and reclaims per-node worktrees with git plumbing kept in here."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def provision(self, graph_node: GraphNode) -> WorkTree:
        node_id = graph_node.id
        project_root = graph_node.project_root
        base_branch = graph_node.base_branch
        path = graph_node.workspace_path / node_id
        if path.is_dir():
            return WorkTree(
                name=node_id, absolute_path=str(path), created_at=datetime.now(UTC)
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        fetch_result = await self._run_git(project_root, ("fetch", REMOTE, base_branch))
        base_ref = "FETCH_HEAD" if fetch_result.returncode == 0 else base_branch
        resolve_result = await self._run_git(
            project_root, ("rev-parse", "--verify", f"{base_ref}^{{commit}}")
        )
        if resolve_result.returncode != 0:
            raise WorktreeError(
                f"could not resolve {base_branch} for {node_id} in "
                f"{project_root}: {resolve_result.stderr.strip()}"
            )

        commit = resolve_result.stdout.strip()
        result = await self._run_git(
            project_root, ("worktree", "add", "--detach", str(path), commit)
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"could not provision a worktree for {node_id} at "
                f"{base_branch}: {result.stderr.strip()}"
            )

        return WorkTree(
            name=node_id, absolute_path=str(path), created_at=datetime.now(UTC)
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

    async def remove(self, worktree: WorkTree) -> None:
        result = await self._run_git(
            Path(worktree.absolute_path),
            ("worktree", "remove", "--force", worktree.absolute_path),
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"could not remove the worktree of {worktree.name}: "
                f"{result.stderr.strip()}"
            )

    async def _run_git(self, cwd: Path, argv: tuple[str, ...]) -> RunResult:
        return await asyncio.to_thread(
            self._command_runner.run, ("git", "-C", str(cwd), *argv)
        )

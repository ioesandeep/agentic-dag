from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.infra.workspace.git_workspace import GitWorkspace

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 1, tzinfo=UTC)
PROJECT_ROOT = Path("/projects/spacy")


async def test_cuts_the_worktree_at_fetch_head_when_the_fetch_succeeds(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout="1c0ffee\n")

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=PROJECT_ROOT,
        workspace_path=tmp_path,
        base_branch="develop",
    )

    worktree = await workspace.provision(graph_node)

    assert command_runner.run.call_args_list == [
        call(("git", "-C", str(PROJECT_ROOT), "fetch", "origin", "develop")),
        call(
            (
                "git",
                "-C",
                str(PROJECT_ROOT),
                "rev-parse",
                "--verify",
                "FETCH_HEAD^{commit}",
            )
        ),
        call(
            (
                "git",
                "-C",
                str(PROJECT_ROOT),
                "worktree",
                "add",
                "--detach",
                str(tmp_path / "A"),
                "1c0ffee",
            )
        ),
    ]
    assert worktree.name == "A"


async def test_resolves_the_local_ref_when_the_fetch_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [
        RunResult(returncode=1, stderr="git said no"),
        RunResult(returncode=0, stdout="1c0ffee\n"),
        RunResult(returncode=0),
    ]

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=PROJECT_ROOT,
        workspace_path=tmp_path,
        base_branch="develop",
    )

    await workspace.provision(graph_node)

    assert command_runner.run.call_args_list[1] == call(
        ("git", "-C", str(PROJECT_ROOT), "rev-parse", "--verify", "develop^{commit}")
    )


async def test_returns_the_existing_worktree_when_its_directory_is_already_there(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    (tmp_path / "A").mkdir()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=PROJECT_ROOT,
        workspace_path=tmp_path,
        base_branch="develop",
    )

    worktree = await workspace.provision(graph_node)

    assert worktree.absolute_path == str(tmp_path / "A")
    command_runner.run.assert_not_called()


async def test_reclaims_from_the_worktree_itself_when_removing(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)

    workspace = GitWorkspace(command_runner=command_runner)
    worktree = WorkTree(name="A", absolute_path="/ws/A", created_at=NOW)

    await workspace.remove(worktree)

    command_runner.run.assert_called_once_with(
        ("git", "-C", "/ws/A", "worktree", "remove", "--force", "/ws/A")
    )


async def test_returns_what_the_agent_left_checked_out_when_reading_the_branch(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout="virgo/a\n")

    workspace = GitWorkspace(command_runner=command_runner)
    worktree = WorkTree(name="A", absolute_path="/ws/A", created_at=NOW)

    branch = await workspace.get_branch(worktree)

    assert branch == "virgo/a"
    command_runner.run.assert_called_once_with(
        ("git", "-C", "/ws/A", "branch", "--show-current")
    )


@pytest.mark.parametrize(
    "act",
    ["provision", "get_branch", "remove"],
    ids=["provisioning", "reading-the-branch", "removing"],
)
async def test_raises_when_git_refuses(
    act: str, mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=1, stderr="git said no")

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT, workspace_path=tmp_path)
    worktree = WorkTree(name="A", absolute_path="/ws/A", created_at=NOW)

    with pytest.raises(WorktreeError, match="git said no"):
        if act == "provision":
            await workspace.provision(graph_node)
        elif act == "get_branch":
            await workspace.get_branch(worktree)
        else:
            await workspace.remove(worktree)

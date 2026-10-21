import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

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
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.host.subprocess_command_runner import (
    SubprocessCommandRunner,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.infra.workspace.git_workspace import GitWorkspace

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 1, tzinfo=UTC)
PROJECT_ROOT = Path("/projects/spacy")


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    commands = [
        ("init", "-q", "-b", "develop"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "Test"),
        ("commit", "-q", "--allow-empty", "-m", "test: initialize repository"),
        ("remote", "add", "origin", str(project_root)),
    ]

    for command in commands:
        subprocess.run(
            ("git", "-C", str(project_root), *command), check=True, capture_output=True
        )

    return project_root


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

    git_command = ("git", "-C", str(PROJECT_ROOT))
    expected_commands = [
        (*git_command, "fetch", "origin", "develop"),
        (*git_command, "rev-parse", "--verify", "FETCH_HEAD^{commit}"),
        (*git_command, "worktree", "prune"),
        (*git_command, "worktree", "add", "--detach", str(tmp_path / "A"), "1c0ffee"),
    ]

    actual_commands = [command.args[0] for command in command_runner.run.call_args_list]

    assert actual_commands == expected_commands
    assert worktree.name == "A"


async def test_resolves_the_local_ref_when_the_fetch_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [
        RunResult(returncode=1, stderr="git said no"),
        RunResult(returncode=0, stdout="1c0ffee\n"),
        RunResult(returncode=0),
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


@pytest.mark.parametrize("is_directory_deleted", [False, True])
async def test_remove_unregisters_the_worktree_when_the_directory_is_present_or_deleted(
    is_directory_deleted: bool, git_repository: Path, tmp_path: Path
) -> None:
    command_runner = SubprocessCommandRunner()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=git_repository,
        workspace_path=tmp_path,
        base_branch="develop",
    )

    worktree = await workspace.provision(graph_node)
    path = Path(worktree.absolute_path)
    if is_directory_deleted:
        shutil.rmtree(path)

    await workspace.remove(worktree, git_repository)

    worktree_list = command_runner.run(
        ("git", "-C", str(git_repository), "worktree", "list", "--porcelain")
    )

    assert not path.exists()
    assert worktree.absolute_path not in worktree_list.stdout


@pytest.mark.parametrize("is_directory_deleted", [False, True])
async def test_provision_returns_a_worktree_when_a_registered_directory_is_present_or_deleted(
    is_directory_deleted: bool, git_repository: Path, tmp_path: Path
) -> None:
    command_runner = SubprocessCommandRunner()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=git_repository,
        workspace_path=tmp_path,
        base_branch="develop",
    )

    worktree = await workspace.provision(graph_node)
    if is_directory_deleted:
        shutil.rmtree(worktree.absolute_path)

    replacement = await workspace.provision(graph_node)

    git_path = tmp_path / "A" / ".git"

    assert replacement.absolute_path == worktree.absolute_path
    assert git_path.is_file()


async def test_provision_returns_a_worktree_when_the_fallback_fetch_creates_the_base_ref(
    git_repository: Path, tmp_path: Path
) -> None:
    command_runner = SubprocessCommandRunner()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=git_repository,
        workspace_path=tmp_path,
        base_branch="origin/develop",
    )

    worktree = await workspace.provision(graph_node)

    git_path = tmp_path / "A" / ".git"

    assert worktree.name == "A"
    assert git_path.is_file()


@pytest.mark.parametrize("is_foreign_worktree", [False, True])
async def test_provision_raises_conflict_when_the_directory_is_not_registered(
    is_foreign_worktree: bool, git_repository: Path, tmp_path: Path
) -> None:
    path = tmp_path / "A"
    if is_foreign_worktree:
        foreign_root = tmp_path / "foreign"
        subprocess.run(
            ("git", "clone", "-q", str(git_repository), str(foreign_root)), check=True
        )

        subprocess.run(
            ("git", "-C", str(foreign_root), "worktree", "add", "--detach", str(path)),
            check=True,
            capture_output=True,
        )
    else:
        path.mkdir()

    command_runner = SubprocessCommandRunner()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=git_repository, workspace_path=tmp_path)

    with pytest.raises(WorktreeConflictError, match="not a registered worktree"):
        await workspace.provision(graph_node)

    assert path.is_dir()


async def test_provision_raises_missing_base_when_the_remote_has_no_branch(
    git_repository: Path, tmp_path: Path
) -> None:
    command_runner = SubprocessCommandRunner()

    workspace = GitWorkspace(command_runner=command_runner)
    graph_node = GraphNode(
        id="A",
        project_root=git_repository,
        workspace_path=tmp_path,
        base_branch="missing",
    )

    with pytest.raises(
        BaseBranchMissingError, match="base branch missing does not resolve"
    ):
        await workspace.provision(graph_node)


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
            await workspace.remove(worktree, PROJECT_ROOT)

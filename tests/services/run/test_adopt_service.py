import io
import subprocess
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.adopt_command import AdoptCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.host.subprocess_command_runner import (
    SubprocessCommandRunner,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_node_repo import (
    InMemoryNodeRepo,
)
from virgo_agentic_dag.infra.workspace.git_workspace import GitWorkspace
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader
from virgo_agentic_dag.services.run.adopt_service import AdoptService
from virgo_agentic_dag.services.run.adopted_node_importer import AdoptedNodeImporter

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 8, 4, tzinfo=UTC)
PR_NUMBER = 412
REPOSITORY = "acme/virgo"
PR_URL = f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}"
HEAD_BRANCH = "human/half-done"
PR_TITLE = "feat(auth): add the login page"

AdoptCall = Callable[..., Awaitable[ExitCode]]


def run_git(repo: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", *argv], cwd=repo, check=True, capture_output=True, text=True
    )

    return done.stdout.strip()


def build_checkout(checkout: Path) -> Path:
    checkout.mkdir()
    run_git(checkout, "init", "-q", "-b", "develop")
    run_git(checkout, "config", "user.email", "t@t")
    run_git(checkout, "config", "user.name", "t")

    (checkout / "README.md").write_text("seed\n", encoding="utf-8")
    run_git(checkout, "add", ".")
    run_git(checkout, "commit", "-q", "-m", "seed")

    run_git(checkout, "checkout", "-q", "-b", HEAD_BRANCH)
    (checkout / "half-done.md").write_text("someone started this\n", encoding="utf-8")
    run_git(checkout, "add", ".")
    run_git(checkout, "commit", "-q", "-m", "half done")
    run_git(checkout, "checkout", "-q", "develop")

    return checkout


def build_details() -> PullRequestDetails:
    return PullRequestDetails(
        number=PR_NUMBER,
        repository=REPOSITORY,
        url=PR_URL,
        head_branch=HEAD_BRANCH,
        title=PR_TITLE,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return build_checkout(tmp_path / "repo")


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path / "ws"


@pytest.fixture
def dag_path(repo: Path, workspace_path: Path, tmp_path: Path) -> Path:
    db_path = tmp_path / "db.sqlite3"
    db_path.touch()

    path = tmp_path / "dag.toml"
    path.write_text(
        f'name = "demo"\n'
        f'project_root = "{repo}"\n'
        f'workspace_path = "{workspace_path}"\n'
        f'db_path = "{db_path}"\n'
        f'executor_agent = "claude"\n'
        f"\n"
        f"[[nodes]]\n"
        f'id = "A"\n'
        f'brief = "the node the run started itself"\n',
        encoding="utf-8",
    )

    return path


@pytest.fixture
def node_repo(mocker: MockerFixture) -> NodeRepo:
    return mocker.AsyncMock(spec=NodeRepo, wraps=InMemoryNodeRepo())


@pytest.fixture
def node_agent_repo(mocker: MockerFixture) -> NodeAgentRepo:
    return mocker.AsyncMock(spec=NodeAgentRepo)


@pytest.fixture
def audit_entry_repo(mocker: MockerFixture) -> AuditEntryRepo:
    return mocker.AsyncMock(spec=AuditEntryRepo)


@pytest.fixture
def code_repo(mocker: MockerFixture) -> CodeRepo:
    repo = mocker.AsyncMock(spec=CodeRepo)
    repo.get_pr_details_from_url.return_value = build_details()
    repo.get_repo_slug.return_value = REPOSITORY

    return repo


@pytest.fixture
def notification_publisher(mocker: MockerFixture) -> NotificationPublisher:
    return mocker.MagicMock(spec=NotificationPublisher)


@pytest.fixture
def agent_launcher(mocker: MockerFixture) -> AgentLauncher:
    launcher = mocker.AsyncMock(spec=AgentLauncher)
    launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    return launcher


@pytest.fixture
def out() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def service(
    code_repo: CodeRepo,
    node_repo: NodeRepo,
    node_agent_repo: NodeAgentRepo,
    audit_entry_repo: AuditEntryRepo,
    notification_publisher: NotificationPublisher,
    agent_launcher: AgentLauncher,
) -> AdoptService:
    return AdoptService(
        dag_loader=TomlDagLoader(),
        code_repo=code_repo,
        node_repo=node_repo,
        node_importer=AdoptedNodeImporter(
            workspace=GitWorkspace(SubprocessCommandRunner()),
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers={executor: agent_launcher for executor in ExecutorAgent},
        ),
    )


@pytest.fixture
def adopt(service: AdoptService, dag_path: Path, out: io.StringIO) -> AdoptCall:
    async def _adopt(
        pr: str = PR_URL,
        node_id: str = "TAKEOVER",
        session: str = "",
        project_root: Path | None = None,
        workspace_path: Path | None = None,
        executor: ExecutorAgent | None = None,
    ) -> ExitCode:
        command = AdoptCommand(
            dag_path=dag_path,
            pr=pr,
            node_id=node_id,
            session=session,
            project_root=project_root,
            workspace_path=workspace_path,
            executor=executor,
        )
        token = bind_context(ApplicationContext(command, out))

        try:
            return await service.adopt(command)
        finally:
            unbind_context(token)

    return _adopt


@pytest.mark.parametrize("override", [None, ExecutorAgent.CLAUDE])
async def test_adopt_uses_the_command_executor_when_given_and_the_dag_executor_when_not(
    adopt: AdoptCall,
    dag_path: Path,
    node_agent_repo: NodeAgentRepo,
    override: ExecutorAgent | None,
) -> None:
    dag_path.write_text(dag_path.read_text().replace('"claude"', '"codex"'))

    exit_code = await adopt(executor=override)

    agent = node_agent_repo.save.await_args.args[0]
    assert exit_code is ExitCode.SUCCESS
    assert agent.name == (override or ExecutorAgent.CODEX).value


async def test_adopt_launches_the_agent_in_a_worktree_cut_from_the_pull_request(
    adopt: AdoptCall,
    repo: Path,
    workspace_path: Path,
    node_repo: NodeRepo,
    node_agent_repo: NodeAgentRepo,
    audit_entry_repo: AuditEntryRepo,
    notification_publisher: NotificationPublisher,
    agent_launcher: AgentLauncher,
) -> None:
    exit_code = await adopt()

    agent = node_agent_repo.save.await_args.args[0]
    audit_entry = audit_entry_repo.save.await_args.args[0]
    node_event = notification_publisher.publish.call_args.args[0]
    worktree_path = workspace_path / "TAKEOVER"
    assert exit_code is ExitCode.SUCCESS
    node_repo.update_state.assert_awaited_once_with(
        "TAKEOVER", NodeState.IN_PROGRESS, ANY
    )
    assert agent.worktree is not None
    assert agent.worktree.pr_number == PR_NUMBER
    assert agent.worktree.branch == HEAD_BRANCH
    assert len(agent.sessions) == 1
    assert agent_launcher.launch.await_args.args[2].resume_token == agent.resume_token
    assert run_git(worktree_path, "rev-parse", "HEAD") == run_git(
        repo, "rev-parse", HEAD_BRANCH
    )
    assert audit_entry.state == NodeState.IN_PROGRESS.value
    assert node_event.type is NotificationType.PR_ADOPTED
    assert node_event.pr_details is not None
    assert node_event.pr_details.number == PR_NUMBER


async def test_adopt_uses_project_root_from_command(
    adopt: AdoptCall, tmp_path: Path
) -> None:
    other_repo = build_checkout(tmp_path / "other-repo")
    other_workspace = tmp_path / "other-ws"

    exit_code = await adopt(project_root=other_repo, workspace_path=other_workspace)

    worktree_path = other_workspace / "TAKEOVER"
    assert exit_code is ExitCode.SUCCESS
    assert run_git(worktree_path, "rev-parse", "HEAD") == run_git(
        other_repo, "rev-parse", HEAD_BRANCH
    )


async def test_adopt_raises_config_error_on_repository_mismatch(
    adopt: AdoptCall, repo: Path, node_repo: NodeRepo, code_repo: CodeRepo
) -> None:
    code_repo.get_repo_slug.return_value = "someone/elsewhere"

    with pytest.raises(ConfigError, match=REPOSITORY):
        await adopt(project_root=repo)

    node_repo.ensure_rows.assert_not_awaited()


async def test_adopt_clones_repository_when_no_checkout_matches(
    adopt: AdoptCall, workspace_path: Path, code_repo: CodeRepo
) -> None:
    code_repo.get_repo_slug.return_value = "someone/elsewhere"
    code_repo.clone_repository.side_effect = lambda repository, destination: (
        build_checkout(destination)
    )

    exit_code = await adopt()

    clone_root = workspace_path / "virgo"
    assert exit_code is ExitCode.SUCCESS
    code_repo.clone_repository.assert_awaited_once_with(REPOSITORY, clone_root)
    assert run_git(workspace_path / "TAKEOVER", "rev-parse", "HEAD") == run_git(
        clone_root, "rev-parse", HEAD_BRANCH
    )


async def test_adopt_raises_spec_error_when_pr_is_not_a_url(
    adopt: AdoptCall, code_repo: CodeRepo
) -> None:
    with pytest.raises(SpecError, match="url"):
        await adopt(pr="412")

    code_repo.get_pr_details_from_url.assert_not_awaited()


async def test_adopt_defaults_node_id_to_pr_number(
    adopt: AdoptCall, node_repo: NodeRepo
) -> None:
    await adopt(node_id="")

    node_repo.update_state.assert_awaited_once_with(
        f"PR-{PR_NUMBER}", NodeState.IN_PROGRESS, ANY
    )


async def test_adopt_titles_the_node_with_the_pull_request_title(
    adopt: AdoptCall, node_repo: NodeRepo
) -> None:
    await adopt()

    seeded = node_repo.ensure_rows.await_args.args[0]
    assert [node.title for node in seeded] == [PR_TITLE]


async def test_adopt_launches_with_a_takeover_brief_when_it_is_given_no_session(
    adopt: AdoptCall, agent_launcher: AgentLauncher
) -> None:
    await adopt()

    brief = agent_launcher.launch.await_args.args[1]
    assert PR_URL in brief
    assert HEAD_BRANCH in brief
    assert "review thread" in brief


async def test_adopt_rests_on_the_given_session_without_launching(
    adopt: AdoptCall,
    node_repo: NodeRepo,
    node_agent_repo: NodeAgentRepo,
    agent_launcher: AgentLauncher,
) -> None:
    await adopt(session="s-42")

    agent = node_agent_repo.save.await_args.args[0]
    assert agent.resume_token == "s-42"
    assert agent.sessions == []
    node_repo.update_state.assert_awaited_once_with("TAKEOVER", NodeState.RESTING, ANY)
    agent_launcher.launch.assert_not_awaited()


async def test_adopt_records_the_session_it_resumes_rather_than_a_composed_sentence(
    adopt: AdoptCall, audit_entry_repo: AuditEntryRepo
) -> None:
    await adopt(session="s-42")

    entry = audit_entry_repo.save.await_args.args[0]
    assert entry.note == (
        f"took over #{PR_NUMBER} on {HEAD_BRANCH} "
        "and will resume the session it was given"
    )


async def test_adopt_fails_when_run_database_is_missing(
    adopt: AdoptCall, tmp_path: Path, node_repo: NodeRepo, code_repo: CodeRepo
) -> None:
    (tmp_path / "db.sqlite3").unlink()

    exit_code = await adopt()

    assert exit_code is ExitCode.FAILURE
    code_repo.get_pr_details_from_url.assert_not_awaited()
    node_repo.ensure_rows.assert_not_awaited()


async def test_adopt_fails_when_node_id_is_taken(
    adopt: AdoptCall, node_repo: NodeRepo, node_agent_repo: NodeAgentRepo
) -> None:
    node_repo.read.return_value = Node(
        id="A", state=NodeState.RESTING.value, created_at=NOW, updated_at=NOW
    )

    exit_code = await adopt(node_id="A")

    assert exit_code is ExitCode.FAILURE
    node_agent_repo.save.assert_not_awaited()

import io
import subprocess
import tomllib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
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
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
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
from virgo_agentic_dag.services.run.node_importer import NodeImporter

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 8, 4, tzinfo=UTC)
PR_NUMBER = 412
REPOSITORY = "acme/virgo"
PR_URL = f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}"
HEAD_BRANCH = "human/half-done"
PR_TITLE = "feat(auth): add the login page"

AdoptCall = Callable[..., Awaitable[ExitCode]]


@dataclass(frozen=True)
class AdoptCommandWithNodeOverrides(AdoptCommand):
    name: str = ""
    depends_on: tuple[str, ...] = ()
    cooldown_seconds: int | None = None


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
    node_agent_repo = mocker.AsyncMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None

    return node_agent_repo


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
    dag_loader = TomlDagLoader()
    graph_builder = GraphBuilder(dag_loader=dag_loader)

    return AdoptService(
        dag_loader=dag_loader,
        graph_builder=graph_builder,
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

    dag_loader = TomlDagLoader()

    exit_code = await adopt(executor=override)

    agent = node_agent_repo.save.await_args.args[0]

    assert exit_code is ExitCode.SUCCESS
    assert agent.name == (override or ExecutorAgent.CODEX).value

    dag_spec = dag_loader.load(dag_path)

    assert dag_spec.nodes[-1].executor_agent is override


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

    assert exit_code is ExitCode.SUCCESS
    node_repo.update_state.assert_awaited_once_with(
        "TAKEOVER", NodeState.IN_PROGRESS, ANY
    )

    assert agent.worktree is not None
    assert agent.worktree.pr_number == PR_NUMBER
    assert agent.worktree.pr_url == PR_URL
    assert agent.worktree.branch == HEAD_BRANCH

    assert len(agent.sessions) == 1
    assert agent_launcher.launch.await_args.args[2].resume_token == agent.resume_token

    worktree_path = workspace_path / "TAKEOVER"

    assert run_git(worktree_path, "rev-parse", "HEAD") == run_git(
        repo, "rev-parse", HEAD_BRANCH
    )

    assert audit_entry.state == NodeState.IN_PROGRESS.value

    assert node_event.type is NotificationType.PR_ADOPTED
    assert node_event.pr_details is not None
    assert node_event.pr_details.number == PR_NUMBER
    assert node_event.pr_details.url == PR_URL


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


@pytest.mark.parametrize("with_overrides", [False, True])
async def test_adopt_appends_a_node_for_the_next_graph_without_changing_existing_bytes(
    dag_path: Path,
    repo: Path,
    workspace_path: Path,
    mocker: MockerFixture,
    with_overrides: bool,
) -> None:
    original_bytes = dag_path.read_bytes()
    original_bytes = original_bytes.replace(b"\n", b"\r\n")
    original_bytes = original_bytes.rstrip(b"\r\n")
    dag_path.write_bytes(original_bytes)

    pr_details = build_details()
    pr_details = replace(pr_details, title='Add "login"\\page\n\t\U0001f680\x7f')

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details
    code_repo.get_repo_slug.return_value = REPOSITORY

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = None

    dag_loader = TomlDagLoader()
    graph_builder = GraphBuilder(dag_loader=dag_loader)

    node_importer = mocker.MagicMock(spec=NodeImporter)
    mocker.patch("virgo_agentic_dag.services.run.adopt_service.emit")
    service = AdoptService(
        dag_loader=dag_loader,
        graph_builder=graph_builder,
        code_repo=code_repo,
        node_repo=node_repo,
        node_importer=node_importer,
    )

    command_type: type[AdoptCommand] = AdoptCommand
    node_overrides: dict[str, object] = {}
    if with_overrides:
        command_type = AdoptCommandWithNodeOverrides
        node_overrides = {
            "name": "Adopted agent",
            "depends_on": ("A",),
            "cooldown_seconds": 0,
        }

    session = 'session-"42"\\\n' if with_overrides else ""
    project_root = repo if with_overrides else None
    node_workspace_path = workspace_path / 'work "login"\\' if with_overrides else None
    command = command_type(
        dag_path=dag_path,
        pr=PR_URL,
        node_id="TAKEOVER",
        session=session,
        project_root=project_root,
        workspace_path=node_workspace_path,
        **node_overrides,
    )

    exit_code = await service.adopt(command)

    assert exit_code is ExitCode.SUCCESS

    updated_bytes = dag_path.read_bytes()

    assert updated_bytes[: len(original_bytes)] == original_bytes

    updated_text = updated_bytes.decode("utf-8")
    node_table = tomllib.loads(updated_text)["nodes"][-1]
    imported_node = node_importer.import_node.await_args.args[0]

    assert node_table["id"] == "TAKEOVER"
    assert node_table["title"] == pr_details.title
    assert node_table["pr"] == PR_URL
    assert node_table["instructions"] == imported_node.instructions

    dag_spec = dag_loader.load(dag_path)
    graph = graph_builder.build_from_path(dag_path)

    assert dag_spec.nodes[-1].session == session
    assert [node.id for node in graph.nodes] == ["A", "TAKEOVER"]
    if with_overrides:
        assert node_table["project_root"] == str(project_root)
        assert node_table["workspace_path"] == str(node_workspace_path)

        assert node_table["cooldown_seconds"] == 0
        assert dag_spec.nodes[-1].depends_on == ("A",)
        assert imported_node.depends_on == ("A",)

        assert imported_node.name == "Adopted agent"
        assert node_table["name"] == imported_node.name
    else:
        assert set(node_table) == {"id", "title", "pr", "instructions"}


@pytest.mark.parametrize("failure", ["append", "reload"])
async def test_adopt_reports_graph_file_failure_and_preserves_imported_rows(
    dag_path: Path,
    mocker: MockerFixture,
    failure: str,
) -> None:
    toml_dag_loader = TomlDagLoader()
    dag_spec = toml_dag_loader.load(dag_path)

    dag_loader = mocker.MagicMock(spec=DagLoader)
    if failure == "append":
        dag_loader.load.return_value = dag_spec
        append_error = PermissionError("not writable")
        mocker.patch.object(Path, "open", side_effect=append_error)
    else:
        dag_loader.load.side_effect = [dag_spec, SpecError("invalid appended table")]

    pr_details = build_details()
    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details
    code_repo.get_repo_slug.return_value = REPOSITORY

    inmemory_node_repo = InMemoryNodeRepo()
    node_repo = mocker.AsyncMock(spec=NodeRepo, wraps=inmemory_node_repo)

    worktree_path = str(dag_path.parent)
    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="TAKEOVER", absolute_path=worktree_path, created_at=NOW
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_importer = AdoptedNodeImporter(
        workspace=workspace,
        node_repo=node_repo,
        node_agent_repo=node_agent_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        agent_launchers={},
    )

    emit = mocker.patch("virgo_agentic_dag.services.run.adopt_service.emit")
    graph_builder = GraphBuilder(dag_loader=dag_loader)
    service = AdoptService(
        dag_loader=dag_loader,
        graph_builder=graph_builder,
        code_repo=code_repo,
        node_repo=node_repo,
        node_importer=node_importer,
    )

    command = AdoptCommand(
        dag_path=dag_path, pr=PR_URL, node_id="TAKEOVER", session="s-42"
    )

    exit_code = await service.adopt(command)

    node = await node_repo.read("TAKEOVER")
    agent = node_agent_repo.save.await_args.args[0]
    output = emit.call_args.args[0]

    assert exit_code is ExitCode.FAILURE
    assert node is not None
    assert node.state == NodeState.RESTING.value
    assert agent.resume_token == "s-42"

    assert str(dag_path) in output
    assert "The imported database rows remain." in output
    assert "The next pass supervises it." not in output

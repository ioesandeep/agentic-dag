from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler import (
    InProgressNodeHandler,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)

BuildAgent = Callable[[WorkTree, AgentSession], NodeAgent]


@pytest.fixture
def build_agent() -> BuildAgent:
    return lambda worktree, session: NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="token",
        node_id="A",
        worktree=worktree,
        sessions=[session],
    )


@pytest.mark.parametrize(
    ("executor_agent", "session_status"),
    [
        (ExecutorAgent.CLAUDE, SessionStatus.ALIVE),
        (None, SessionStatus.FINISHED),
    ],
    ids=["session-alive", "no-launcher-for-its-agent"],
)
async def test_leaves_the_node_in_progress_when_the_session_cannot_be_settled(
    executor_agent: ExecutorAgent | None,
    session_status: SessionStatus,
    mocker: MockerFixture,
    build_agent: BuildAgent,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=executor_agent)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", branch="", pr_number=0, created_at=NOW
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = session_status

    node_repo = mocker.MagicMock(spec=NodeRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=mocker.MagicMock(spec=Workspace),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=mocker.MagicMock(spec=CodeRepo),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_session_repo.close.assert_not_awaited()
    audit_entry_repo.save.assert_not_awaited()


@pytest.mark.parametrize(
    ("branch", "found_pr_number", "worktree_pr", "worktree_branch", "expected_kind"),
    [
        ("virgo/a", 12, 0, "", NotificationType.PR_OPENED),
        ("", 0, 12, "virgo/a", NotificationType.PR_UPDATED),
    ],
    ids=["first-pull-request", "known-pull-request"],
)
async def test_rests_the_node_when_the_session_reached_a_pull_request(
    branch: str,
    found_pr_number: int,
    worktree_pr: int,
    worktree_branch: str,
    expected_kind: NotificationType,
    mocker: MockerFixture,
    build_agent: BuildAgent,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch=worktree_branch,
        pr_number=worktree_pr,
        created_at=NOW,
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = branch

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.find_pull_request.return_value = found_pr_number
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN,
        head_sha="8bddf07abcdef",
        base_branch="main",
        title="Add a digest helper",
    )

    node_repo = mocker.MagicMock(spec=NodeRepo)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=work_tree_repo,
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=code_repo,
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )
    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.RESTING, NOW)
    work_tree_repo.record_publication.assert_awaited_once()
    published = work_tree_repo.record_publication.await_args.args[0]
    assert (
        published.id,
        published.branch,
        published.pr_number,
        published.head_sha,
    ) == (1, "virgo/a", 12, "8bddf07abcdef")
    agent_session_repo.close.assert_awaited_once()
    closed = agent_session_repo.close.await_args.args[0]
    assert (closed.id, closed.end_state) == (1, "finished")
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is expected_kind
    assert event.pr_details is not None and event.pr_details.number == 12


@pytest.mark.parametrize(
    ("session_status", "expected_state", "expected_kind", "expected_reason"),
    [
        (
            SessionStatus.FINISHED,
            NodeState.NEEDS_HUMAN,
            NotificationType.NEEDS_HUMAN,
            "its session finished without opening a pull request",
        ),
        (
            SessionStatus.OVERDUE,
            NodeState.ERRORED,
            NotificationType.AGENT_FAILED,
            "its session ran past its deadline and was killed",
        ),
    ],
    ids=["finished", "overdue"],
)
async def test_stops_the_node_when_the_session_ended_without_a_pull_request(
    session_status: SessionStatus,
    expected_state: NodeState,
    expected_kind: NotificationType,
    expected_reason: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", branch="", pr_number=0, created_at=NOW
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = session_status

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = ""

    node_repo = mocker.MagicMock(spec=NodeRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=work_tree_repo,
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=mocker.MagicMock(spec=CodeRepo),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )
    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", expected_state, NOW)
    work_tree_repo.record_publication.assert_not_awaited()
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is expected_kind
    assert event.reason == expected_reason


async def test_rests_the_node_when_an_overdue_session_had_published(
    mocker: MockerFixture, build_agent: BuildAgent
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", branch="", pr_number=0, created_at=NOW
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.OVERDUE

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = "virgo/a"

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.find_pull_request.return_value = 7
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN, head_sha="8bddf07abcdef", base_branch="main"
    )

    node_repo = mocker.MagicMock(spec=NodeRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=work_tree_repo,
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=code_repo,
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )
    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.RESTING, NOW)
    agent_launcher.stop.assert_awaited_once()
    assert agent_launcher.stop.await_args.args[0].pid == 4242
    work_tree_repo.record_publication.assert_awaited_once()
    published = work_tree_repo.record_publication.await_args.args[0]
    assert (published.id, published.branch, published.pr_number) == (1, "virgo/a", 7)


async def test_errors_the_node_when_no_agent_was_ever_recorded(
    mocker: MockerFixture,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None

    node_repo = mocker.MagicMock(spec=NodeRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=mocker.MagicMock(spec=Workspace),
        agent_launchers={ExecutorAgent.CLAUDE: mocker.MagicMock(spec=AgentLauncher)},
        code_repo=mocker.MagicMock(spec=CodeRepo),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )
    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.ERRORED, NOW)
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.AGENT_FAILED


async def test_leaves_the_node_in_progress_when_the_platform_cannot_be_read(
    mocker: MockerFixture, build_agent: BuildAgent
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", branch="", pr_number=0, created_at=NOW
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = "virgo/a"

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.find_pull_request.side_effect = ObservationError(
        "the platform is unreachable"
    )

    node_repo = mocker.MagicMock(spec=NodeRepo)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=code_repo,
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_session_repo.close.assert_not_awaited()


@pytest.mark.parametrize(
    ("exit_text", "expected_log_tail"),
    [("1\n", "Error: Reached max turns (120)"), ("0\n", "")],
    ids=["nonzero-exit", "clean-exit"],
)
async def test_publishes_the_log_tail_on_the_stop_event_only_when_the_session_process_exits_with_a_nonzero_code(
    exit_text: str,
    expected_log_tail: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    tmp_path: Path,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path=str(tmp_path / "A"),
        branch="",
        pr_number=0,
        created_at=NOW,
    )
    (tmp_path / "A.log").write_text("Error: Reached max turns (120)")
    (tmp_path / "A.exit").write_text(exit_text)

    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = ""

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = InProgressNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=mocker.MagicMock(spec=CodeRepo),
    )

    await handler.handle(graph, [graph_node], NOW)

    event = notification_publisher.publish.call_args.args[0]
    assert event.log_tail == expected_log_tail


@pytest.fixture
def log_lines() -> list[str]:
    return [f"line {number}" for number in range(41)]


@pytest.mark.parametrize(
    ("exit_text", "expected_exit_code"),
    [("1\n", 1), (None, None)],
    ids=["exit-file-written", "no-exit-file"],
)
async def test_closes_the_session_with_the_exit_code_and_log_tail_when_the_session_ends(
    exit_text: str | None,
    expected_exit_code: int | None,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    tmp_path: Path,
    log_lines: list[str],
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path=str(tmp_path / "A"),
        branch="",
        pr_number=0,
        created_at=NOW,
    )
    (tmp_path / "A.log").write_text("\n".join(log_lines))
    if exit_text is not None:
        (tmp_path / "A.exit").write_text(exit_text)

    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = ""

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    handler = InProgressNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=workspace,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        code_repo=mocker.MagicMock(spec=CodeRepo),
    )

    await handler.handle(graph, [graph_node], NOW)

    closed = agent_session_repo.close.await_args.args[0]
    expected_log_tail = "\n".join(log_lines[1:])
    assert (closed.exit_code, closed.log_tail) == (
        expected_exit_code,
        expected_log_tail,
    )

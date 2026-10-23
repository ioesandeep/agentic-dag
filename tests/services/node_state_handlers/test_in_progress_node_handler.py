import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
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
from virgo_agentic_dag.domain.infra.agent.usage_limit_reader import UsageLimitReader
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
from virgo_agentic_dag.services.run.node_wait_service import NodeWaitService

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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
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
        url="https://git.example.com/acme/virgo/pull/12",
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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)

    published = work_tree_repo.record_publication.await_args.args[0]
    closed = agent_session_repo.close.await_args.args[0]
    event = notification_publisher.publish.call_args.args[0]

    node_repo.update_state.assert_awaited_once_with("A", NodeState.RESTING, NOW)
    work_tree_repo.record_publication.assert_awaited_once()
    assert (
        published.id,
        published.branch,
        published.pr_number,
        published.pr_url,
        published.head_sha,
    ) == (
        1,
        "virgo/a",
        12,
        "https://git.example.com/acme/virgo/pull/12",
        "8bddf07abcdef",
    )

    agent_session_repo.close.assert_awaited_once()
    assert (closed.id, closed.end_state) == (1, "finished")

    notification_publisher.publish.assert_called_once()
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

    usage_limit_reader = mocker.MagicMock(spec=UsageLimitReader)
    usage_limit_reader.get_reset_time.return_value = None

    node_wait_service = mocker.MagicMock(spec=NodeWaitService)
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
        usage_limit_readers={ExecutorAgent.CLAUDE: usage_limit_reader},
        node_wait_service=node_wait_service,
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)
    event = notification_publisher.publish.call_args.args[0]

    node_repo.update_state.assert_awaited_once_with("A", expected_state, NOW)
    work_tree_repo.record_publication.assert_not_awaited()
    node_wait_service.wait.assert_not_awaited()

    notification_publisher.publish.assert_called_once()
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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)
    published = work_tree_repo.record_publication.await_args.args[0]

    node_repo.update_state.assert_awaited_once_with("A", NodeState.RESTING, NOW)
    agent_launcher.stop.assert_awaited_once()
    assert agent_launcher.stop.await_args.args[0].pid == 4242

    work_tree_repo.record_publication.assert_awaited_once()
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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)
    event = notification_publisher.publish.call_args.args[0]

    node_repo.update_state.assert_awaited_once_with("A", NodeState.ERRORED, NOW)
    notification_publisher.publish.assert_called_once()
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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_session_repo.close.assert_not_awaited()


@pytest.mark.parametrize(
    "failing_operation",
    ["find_pull_request", "get_pull_request", "count_commits_between"],
)
async def test_keeps_the_session_overdue_when_settling_retries_after_a_platform_error(
    failing_operation: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        head_sha="1a2b3c4d5e6f",
        created_at=NOW,
    )

    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.side_effect = [
        SessionStatus.OVERDUE,
        SessionStatus.FINISHED,
    ]

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = "virgo/a"

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.find_pull_request.return_value = 12
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN, head_sha="8bddf07abcdef", base_branch="main"
    )

    code_repo.count_commits_between.return_value = 1

    failing_method = getattr(code_repo, failing_operation)
    observation_error = ObservationError("the platform is unreachable")
    failing_method.side_effect = [observation_error, failing_method.return_value]

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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW

    await handler.handle(graph, [graph_node], NOW)
    recorded_session = agent_session_repo.close.await_args.args[0]

    node_repo.update_state.assert_not_awaited()
    assert recorded_session.end_state == SessionStatus.OVERDUE.value

    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, recorded_session
    )

    await handler.handle(graph, [graph_node], NOW)
    closed_session = agent_session_repo.close.await_args.args[0]

    assert closed_session.end_state == SessionStatus.OVERDUE.value
    node_repo.update_state.assert_awaited_once_with("A", NodeState.RESTING, NOW)


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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
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
        usage_limit_readers={},
        node_wait_service=mocker.MagicMock(spec=NodeWaitService),
    )

    await handler.handle(graph, [graph_node], NOW)

    closed = agent_session_repo.close.await_args.args[0]
    expected_log_tail = "\n".join(log_lines[1:])
    assert (closed.exit_code, closed.log_tail) == (
        expected_exit_code,
        expected_log_tail,
    )


@pytest.mark.parametrize(
    ("executor_agent", "triggered_by", "pr_number", "exit_code"),
    [
        (ExecutorAgent.CLAUDE, "launch", 0, 1),
        (ExecutorAgent.CODEX, "launch", 0, 0),
        (ExecutorAgent.CODEX, "wake", 12, None),
    ],
    ids=["claude-launch", "codex-zero-exit", "resting-node-wake"],
)
async def test_handler_waits_when_an_ended_session_has_a_usage_limit_reset_time(
    executor_agent: ExecutorAgent,
    triggered_by: str,
    pr_number: int,
    exit_code: int | None,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    tmp_path: Path,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=executor_agent)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path=str(tmp_path / "A"),
        branch="virgo/a",
        pr_number=pr_number,
        created_at=NOW,
    )

    log_path = tmp_path / "A.log"
    log_path.write_text("usage-limit output")

    ended_at = NOW - timedelta(minutes=10)
    completion_timestamp = ended_at.timestamp()
    os.utime(log_path, (completion_timestamp, completion_timestamp))

    if exit_code is not None:
        exit_path = tmp_path / "A.exit"
        exit_text = str(exit_code)
        exit_path.write_text(exit_text)
        os.utime(exit_path, (completion_timestamp, completion_timestamp))

    started_at = ended_at - timedelta(hours=1)
    session = AgentSession(
        id=1,
        agent_id="agent-1",
        started_at=started_at,
        triggered_by=triggered_by,
        pid=4242,
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, session)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    reset_time = NOW - timedelta(minutes=5)
    usage_limit_reader = mocker.MagicMock(spec=UsageLimitReader)
    usage_limit_reader.get_reset_time.return_value = reset_time

    node_wait_service = mocker.MagicMock(spec=NodeWaitService)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    node_repo = mocker.MagicMock(spec=NodeRepo)

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)
    handler = InProgressNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=mocker.MagicMock(spec=Workspace),
        agent_launchers={executor_agent: agent_launcher},
        code_repo=code_repo,
        usage_limit_readers={executor_agent: usage_limit_reader},
        node_wait_service=node_wait_service,
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler.datetime"
    )

    clock.now.return_value = NOW
    clock.fromtimestamp.side_effect = datetime.fromtimestamp

    tick_response = await handler.handle(graph, [graph_node], NOW)
    closed_session = agent_session_repo.close.await_args.args[0]

    usage_limit_reader.get_reset_time.assert_called_once_with(
        "usage-limit output", ended_at
    )

    assert tick_response.events_applied == 1
    assert closed_session.end_state == "usage_limit"
    assert closed_session.exit_code == exit_code
    node_wait_service.wait.assert_awaited_once_with(
        "A",
        reset_time,
        f"{executor_agent.value} usage limit resets at {reset_time}",
        NOW,
    )

    node_repo.update_state.assert_not_awaited()
    notification_publisher.publish.assert_not_called()
    code_repo.find_pull_request.assert_not_awaited()

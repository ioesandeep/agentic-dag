import json
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.services.node_state_handlers.resting_node_handler import (
    RestingNodeHandler,
)
from virgo_agentic_dag.services.signals.approval_signal import ApprovalSignal
from virgo_agentic_dag.services.signals.check_signal import CheckSignal
from virgo_agentic_dag.services.signals.comment_signal import CommentSignal
from virgo_agentic_dag.services.signals.conflict_signal import ConflictSignal
from virgo_agentic_dag.services.signals.pr_signal import PrSignal

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)

BuildAgent = Callable[[WorkTree, list[AgentSession]], NodeAgent]
BuildSignals = Callable[[], list[PrSignal]]
BuildNode = Callable[..., Node]


@pytest.fixture
def build_agent() -> BuildAgent:
    return lambda worktree, sessions: NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="token",
        node_id="A",
        worktree=worktree,
        sessions=sessions,
    )


@pytest.fixture
def build_node() -> BuildNode:
    return lambda pull_request_settled_at=None: Node(
        id="A",
        state=NodeState.RESTING.value,
        created_at=NOW,
        updated_at=NOW,
        pull_request_settled_at=pull_request_settled_at,
    )


@pytest.fixture
def build_signals() -> BuildSignals:
    return lambda: [
        CommentSignal(agent_account="virgo-bot"),
        CheckSignal(),
        ConflictSignal(),
        ApprovalSignal(),
    ]


@pytest.mark.parametrize(
    (
        "pr_state",
        "merged_by",
        "is_approved",
        "expected_state",
        "expected_kind",
        "expected_note",
    ),
    [
        (
            PullRequestState.MERGED,
            "mrfawy",
            False,
            NodeState.MERGED,
            NotificationType.MERGED,
            "merged by mrfawy",
        ),
        (
            PullRequestState.MERGED,
            "",
            True,
            NodeState.MERGED,
            NotificationType.APPROVED_AND_MERGED,
            "its pull request merged",
        ),
        (
            PullRequestState.CLOSED,
            "",
            False,
            NodeState.NEEDS_HUMAN,
            NotificationType.NEEDS_HUMAN,
            "its pull request was closed without merging",
        ),
    ],
    ids=["merged", "approved-and-merged", "closed-unmerged"],
)
async def test_settles_the_node_when_the_pull_request_reaches_a_final_state(
    pr_state: PullRequestState,
    merged_by: str,
    is_approved: bool,
    expected_state: NodeState,
    expected_kind: NotificationType,
    expected_note: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_node: BuildNode,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, [launch_session]
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=pr_state,
        head_sha="sha1",
        base_branch="develop",
        merged_by=merged_by,
        is_approved=is_approved,
    )

    node = build_node()
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = node
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        agent_launchers={ExecutorAgent.CLAUDE: mocker.MagicMock(spec=AgentLauncher)},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.resting_node_handler.datetime"
    )
    clock.now.return_value = NOW
    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", expected_state, NOW)
    node_repo.record_pull_request_settled.assert_awaited_once_with(node, NOW)
    audit_entry_repo.save.assert_awaited_once()
    assert audit_entry_repo.save.await_args.args[0].note == expected_note
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert (event.type, event.pr_details.number) == (expected_kind, 12)


async def test_records_no_settle_time_when_the_node_already_records_one(
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_node: BuildNode,
    build_signals: BuildSignals,
) -> None:
    settled_at = datetime(2026, 7, 30, tzinfo=UTC)
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, [launch_session]
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.MERGED, head_sha="sha1", base_branch="develop"
    )

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(pull_request_settled_at=settled_at)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        agent_launchers={ExecutorAgent.CLAUDE: mocker.MagicMock(spec=AgentLauncher)},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.resting_node_handler.datetime"
    )
    clock.now.return_value = NOW
    await handler.handle(graph, [graph_node], NOW)

    node_repo.record_pull_request_settled.assert_not_awaited()
    node_repo.update_state.assert_awaited_once_with("A", NodeState.MERGED, NOW)


@pytest.mark.parametrize(
    ("is_mergeable", "comment_bodies", "expected_phrase"),
    [
        (True, ["please rename this class"], "please rename this class"),
        (False, [], "resolve the conflicts"),
    ],
    ids=["new-comment", "conflict"],
)
async def test_wakes_the_agent_when_a_signal_reports_news(
    is_mergeable: bool,
    comment_bodies: list[str],
    expected_phrase: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE, name="Vesta")
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )
    agent = build_agent(worktree, [launch_session])

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = agent

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN,
        head_sha="sha1",
        base_branch="develop",
        is_mergeable=is_mergeable,
    )
    code_repo.get_review_artifacts.return_value = [
        ReviewArtifact(
            kind=ReviewArtifactType.ISSUE_COMMENT,
            artifact_id=1,
            author="mrfawy",
            body=body,
            created_at="2026-07-30T10:00:00Z",
        )
        for body in comment_bodies
    ]

    wake_session = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=777
    )
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = wake_session

    node_repo = mocker.MagicMock(spec=NodeRepo)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=agent_session_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.resting_node_handler.datetime"
    )
    clock.now.return_value = NOW
    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, NOW)
    node_repo.record_pull_request_settled.assert_not_awaited()
    agent_launcher.wake.assert_awaited_once()
    woken_node, news, woken_agent = agent_launcher.wake.await_args.args
    assert woken_node.id == "A"
    assert woken_agent.resume_token == agent.resume_token
    assert expected_phrase in news
    agent_session_repo.add.assert_awaited_once_with(wake_session)


@pytest.mark.parametrize(
    ("marks", "comment_author"),
    [
        (json.dumps({"comments": "2026-07-30T10:00:00Z"}), "mrfawy"),
        ("{}", "virgo-bot"),
    ],
    ids=["already-marked", "written-by-the-agent"],
)
async def test_leaves_the_node_resting_when_a_comment_is_not_news(
    marks: str,
    comment_author: str,
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks=marks,
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, [launch_session]
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN, head_sha="sha1", base_branch="develop"
    )
    code_repo.get_review_artifacts.return_value = [
        ReviewArtifact(
            kind=ReviewArtifactType.ISSUE_COMMENT,
            artifact_id=1,
            author=comment_author,
            body="please rename this class",
            created_at="2026-07-30T10:00:00Z",
        )
    ]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=work_tree_repo,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_launcher.wake.assert_not_awaited()
    work_tree_repo.advance_marks.assert_not_awaited()


async def test_announces_without_waking_when_the_pull_request_is_approved(
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, [launch_session]
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN,
        head_sha="sha1",
        base_branch="develop",
        is_approved=True,
    )
    code_repo.get_review_artifacts.return_value = []

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=work_tree_repo,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_launcher.wake.assert_not_awaited()
    work_tree_repo.advance_marks.assert_awaited_once()
    marked = work_tree_repo.advance_marks.await_args.args[0]
    assert json.loads(marked.marks)["approval"] == "sha1"
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.APPROVED


async def test_needs_a_human_when_the_wake_budget_is_spent(
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    sessions = [
        AgentSession(
            id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
        ),
        AgentSession(
            id=2, agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=None
        ),
        AgentSession(
            id=3, agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=None
        ),
    ]

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree, sessions)

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN, head_sha="sha1", base_branch="develop"
    )
    code_repo.get_review_artifacts.return_value = [
        ReviewArtifact(
            kind=ReviewArtifactType.ISSUE_COMMENT,
            artifact_id=1,
            author="mrfawy",
            body="please rename this class",
            created_at="2026-07-30T10:00:00Z",
        )
    ]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_repo = mocker.MagicMock(spec=NodeRepo)

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=2)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    clock = mocker.patch(
        "virgo_agentic_dag.services.node_state_handlers.resting_node_handler.datetime"
    )
    clock.now.return_value = NOW
    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.NEEDS_HUMAN, NOW)
    agent_launcher.wake.assert_not_awaited()
    stopped_event = notification_publisher.publish.call_args.args[0]
    assert stopped_event.pr_details.number == 12


async def test_leaves_the_node_resting_when_the_platform_cannot_be_read(
    mocker: MockerFixture,
    build_agent: BuildAgent,
    build_signals: BuildSignals,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        marks="{}",
        created_at=NOW,
    )
    launch_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(
        worktree, [launch_session]
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.side_effect = ObservationError(
        "the platform is unreachable"
    )

    node_repo = mocker.MagicMock(spec=NodeRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    handler = RestingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        agent_launchers={ExecutorAgent.CLAUDE: mocker.MagicMock(spec=AgentLauncher)},
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=build_signals(),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    audit_entry_repo.save.assert_not_awaited()

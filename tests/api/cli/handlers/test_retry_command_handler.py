import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.api.cli.handlers.retry_command_handler import RetryCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.retry_command import RetryCommand
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_audit_entry_repo import (
    InMemoryAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_node_repo import (
    InMemoryNodeRepo,
)
from virgo_agentic_dag.services.run.dependent_release_service import (
    DependentReleaseService,
)
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 8, tzinfo=UTC)
NODE_ID = "TOKENS"


@pytest.fixture
def node_repo() -> InMemoryNodeRepo:
    return InMemoryNodeRepo()


@pytest.fixture
def audit_entry_repo() -> InMemoryAuditEntryRepo:
    return InMemoryAuditEntryRepo()


@pytest.fixture
def notification_publisher(mocker: MockerFixture) -> NotificationPublisher:
    return mocker.MagicMock(spec=NotificationPublisher)


@pytest.fixture
def out() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def handler(
    mocker: MockerFixture,
    node_repo: InMemoryNodeRepo,
    audit_entry_repo: InMemoryAuditEntryRepo,
    notification_publisher: NotificationPublisher,
) -> RetryCommandHandler:
    graph_nodes = [GraphNode(id=NODE_ID)]
    graph = Graph(name="demo", nodes=graph_nodes)

    return RetryCommandHandler(
        mocker.MagicMock(spec=RunLock),
        node_repo,
        audit_entry_repo,
        notification_publisher,
        mocker.MagicMock(spec=NodeAgentRepo),
        mocker.MagicMock(spec=RunScheduleService),
        mocker.MagicMock(spec=DependentReleaseService),
        graph,
    )


async def open_node(node_repo: InMemoryNodeRepo, state: NodeState) -> None:
    await node_repo.ensure_rows([GraphNode(id=NODE_ID)], NOW)
    await node_repo.update_state(NODE_ID, state, NOW)


async def retry(
    handler: RetryCommandHandler, out: io.StringIO, reset: bool = False
) -> ExitCode:
    command = RetryCommand(dag_path=Path("dag.toml"), node_id=NODE_ID, reset=reset)
    token = bind_context(ApplicationContext(command, out))

    try:
        return await handler.handle(command)
    finally:
        unbind_context(token)


@pytest.mark.parametrize("state", [NodeState.ERRORED, NodeState.NEEDS_HUMAN])
async def test_retry_returns_a_stopped_node_to_pending(
    state: NodeState,
    mocker: MockerFixture,
    node_repo: InMemoryNodeRepo,
    audit_entry_repo: InMemoryAuditEntryRepo,
    notification_publisher: NotificationPublisher,
    out: io.StringIO,
) -> None:
    graph_nodes = [GraphNode(id=NODE_ID, recovery_attempts_allowed=1)]
    await node_repo.ensure_rows(graph_nodes, NOW)
    await node_repo.spend_recovery_attempt(NODE_ID)
    await node_repo.update_state(NODE_ID, state, NOW)

    graph_nodes = [GraphNode(id=NODE_ID, recovery_attempts_allowed=5)]
    graph = Graph(name="demo", nodes=graph_nodes)
    handler = RetryCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=mocker.MagicMock(spec=NodeAgentRepo),
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
        graph=graph,
    )

    exit_code = await retry(handler, out)

    node = await node_repo.read(NODE_ID)
    entries = await audit_entry_repo.get_all()
    node_event = notification_publisher.publish.call_args.args[0]

    assert exit_code is ExitCode.SUCCESS
    assert node is not None
    assert node.state == NodeState.PENDING.value
    assert node.recovery_attempts_allowed == 5

    assert entries[0].note == "a human sent it back to work"
    assert node_event.type is NotificationType.RETRIED


async def test_retry_clears_the_resume_token_when_reset_is_set(
    mocker: MockerFixture,
    node_repo: InMemoryNodeRepo,
    audit_entry_repo: InMemoryAuditEntryRepo,
    notification_publisher: NotificationPublisher,
    out: io.StringIO,
) -> None:
    await open_node(node_repo, NodeState.ERRORED)
    worktree = WorkTree(
        id=7, agent_id="agent-1", name=NODE_ID, absolute_path="/ws/A", created_at=NOW
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="first-token",
        node_id=NODE_ID,
        worktree=worktree,
    )

    graph_nodes = [GraphNode(id=NODE_ID, recovery_attempts_allowed=5)]
    graph = Graph(name="demo", nodes=graph_nodes)

    handler = RetryCommandHandler(
        mocker.MagicMock(spec=RunLock),
        node_repo,
        audit_entry_repo,
        notification_publisher,
        node_agent_repo,
        mocker.MagicMock(spec=RunScheduleService),
        mocker.MagicMock(spec=DependentReleaseService),
        graph,
    )

    exit_code = await retry(handler, out, reset=True)

    agent = node_agent_repo.save.await_args.args[0]

    assert exit_code is ExitCode.SUCCESS
    assert agent.id == "agent-1"
    assert agent.resume_token == ""
    assert agent.worktree is not None and agent.worktree.id == 7

    node = await node_repo.read(NODE_ID)
    assert node is not None and node.recovery_attempts_allowed == 5


@pytest.mark.parametrize(
    "state", [NodeState.MERGED, NodeState.IN_PROGRESS, NodeState.RESTING]
)
async def test_retry_refuses_a_node_that_has_not_stopped(
    state: NodeState,
    handler: RetryCommandHandler,
    node_repo: InMemoryNodeRepo,
    audit_entry_repo: InMemoryAuditEntryRepo,
    out: io.StringIO,
) -> None:
    await open_node(node_repo, state)

    exit_code = await retry(handler, out)

    node = await node_repo.read(NODE_ID)

    assert exit_code is ExitCode.FAILURE
    assert node is not None
    assert node.state == state.value

    assert await audit_entry_repo.get_all() == []
    assert state.value in out.getvalue()


async def test_retry_refuses_a_node_that_is_not_in_the_run(
    handler: RetryCommandHandler,
    audit_entry_repo: InMemoryAuditEntryRepo,
    out: io.StringIO,
) -> None:
    exit_code = await retry(handler, out)

    assert exit_code is ExitCode.FAILURE
    assert await audit_entry_repo.get_all() == []
    assert NODE_ID in out.getvalue()


@pytest.mark.parametrize(
    ("state", "is_registered"),
    [
        (NodeState.ERRORED, False),
        (NodeState.ERRORED, True),
        (NodeState.IN_PROGRESS, False),
        (None, False),
    ],
)
async def test_retry_registers_the_run_only_after_a_successful_state_change(
    state: NodeState | None,
    is_registered: bool,
    mocker: MockerFixture,
    out: io.StringIO,
) -> None:
    node = None
    if state is not None:
        node = Node(id=NODE_ID, title="", name="", state=state.value)

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = node

    scheduled_job = ScheduledJob(label="fyi.virgo.dag.demo")
    registered_job = None if is_registered else scheduled_job
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.ensure_registered.return_value = registered_job

    run_lock = mocker.MagicMock(spec=RunLock)

    call_order = mocker.MagicMock()

    call_order.attach_mock(run_lock.acquire_lock, "acquire")
    call_order.attach_mock(node_repo.update_state, "update_state")
    call_order.attach_mock(run_schedule_service.ensure_registered, "ensure_registered")
    call_order.attach_mock(run_lock.release, "release")

    graph_nodes = [GraphNode(id=NODE_ID)]
    graph = Graph(name="demo", nodes=graph_nodes)

    handler = RetryCommandHandler(
        run_lock=run_lock,
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=mocker.MagicMock(spec=NodeAgentRepo),
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
        graph=graph,
    )

    dag_path = Path("dag.toml")
    command = RetryCommand(dag_path=dag_path, node_id=NODE_ID)
    context = ApplicationContext(command, out)
    token = bind_context(context)

    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    if state is not NodeState.ERRORED:
        assert exit_code is ExitCode.FAILURE
        node_repo.reset_recovery_attempts.assert_not_awaited()

        run_schedule_service.ensure_registered.assert_not_awaited()
        assert "this host will run" not in out.getvalue()

        return

    assert exit_code is ExitCode.SUCCESS
    run_schedule_service.ensure_registered.assert_awaited_once_with(dag_path)
    assert [call[0] for call in call_order.mock_calls] == [
        "acquire",
        "update_state",
        "ensure_registered",
        "release",
    ]

    output = out.getvalue()
    has_schedule_message = "this host will run fyi.virgo.dag.demo" in output

    assert has_schedule_message is (not is_registered)


async def test_retry_returns_parked_dependents_to_pending_after_the_parent_restarts(
    mocker: MockerFixture, out: io.StringIO
) -> None:
    graph_nodes = [
        GraphNode(id=NODE_ID),
        GraphNode(id="B", depends_on=(NODE_ID,)),
        GraphNode(id="C", depends_on=(NODE_ID,)),
    ]

    graph = Graph(name="demo", nodes=graph_nodes)

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = Node(id=NODE_ID, state=NodeState.ERRORED.value)
    node_repo.get_nodes_by_ids.return_value = [
        Node(id=node_id, state=NodeState.NEEDS_HUMAN.value) for node_id in ["B", "C"]
    ]

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [
        AuditEntry(
            node_id="B",
            state=NodeState.NEEDS_HUMAN.value,
            note=f"upstream node {NODE_ID} stopped, so this one can never start",
            created_at=NOW,
        )
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    dependent_release_service = DependentReleaseService(
        graph=graph,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
    )

    handler = RetryCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=mocker.MagicMock(spec=NodeAgentRepo),
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
        dependent_release_service=dependent_release_service,
        graph=graph,
    )

    exit_code = await retry(handler, out)

    state_changes = [call.args[:2] for call in node_repo.update_state.await_args_list]

    assert exit_code is ExitCode.SUCCESS
    assert state_changes == [(NODE_ID, NodeState.PENDING), ("B", NodeState.PENDING)]

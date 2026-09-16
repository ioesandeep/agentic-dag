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
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_audit_entry_repo import (
    InMemoryAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_node_repo import (
    InMemoryNodeRepo,
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
    return RetryCommandHandler(
        mocker.MagicMock(spec=RunLock),
        node_repo,
        audit_entry_repo,
        notification_publisher,
        mocker.MagicMock(spec=NodeAgentRepo),
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
    handler: RetryCommandHandler,
    node_repo: InMemoryNodeRepo,
    audit_entry_repo: InMemoryAuditEntryRepo,
    notification_publisher: NotificationPublisher,
    out: io.StringIO,
) -> None:
    await open_node(node_repo, state)

    exit_code = await retry(handler, out)

    node = await node_repo.read(NODE_ID)
    entries = await audit_entry_repo.get_all()
    node_event = notification_publisher.publish.call_args.args[0]
    assert exit_code is ExitCode.SUCCESS
    assert node is not None
    assert node.state == NodeState.PENDING.value
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
    handler = RetryCommandHandler(
        mocker.MagicMock(spec=RunLock),
        node_repo,
        audit_entry_repo,
        notification_publisher,
        node_agent_repo,
    )

    exit_code = await retry(handler, out, reset=True)

    agent = node_agent_repo.save.await_args.args[0]
    assert exit_code is ExitCode.SUCCESS
    assert agent.id == "agent-1"
    assert agent.resume_token == ""
    assert agent.worktree is not None and agent.worktree.id == 7


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

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.run.node_skip_service import NodeSkipService

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 9, 7, tzinfo=UTC)
COMMAND = SkipCommand(dag_path=Path("dag.toml"), node_id="A")

BuildNode = Callable[..., Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id, state, agent=None: Node(
        id=node_id,
        title="",
        name="",
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
        agent=agent,
    )


@pytest.mark.parametrize(
    "state",
    [
        NodeState.PENDING,
        NodeState.RESTING,
        NodeState.ERRORED,
        NodeState.NEEDS_HUMAN,
    ],
)
async def test_skip_marks_the_node_skipped_when_it_is_waiting_or_stopped(
    state: NodeState, mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", state)
    node_repo.get_nodes_by_ids.return_value = []
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = Graph(
        name="demo", nodes=[GraphNode(id="A")]
    )
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        graph_builder=graph_builder,
    )

    pending_node_ids = await service.skip(COMMAND, NOW)

    audit_entry = audit_entry_repo.save.await_args.args[0]
    node_event = notification_publisher.publish.call_args.args[0]
    assert pending_node_ids == []
    node_repo.update_state.assert_awaited_once_with("A", NodeState.SKIPPED, NOW)
    assert audit_entry.state == NodeState.SKIPPED.value
    assert audit_entry.note == "a human skipped it"
    assert node_event.type is NotificationType.SKIPPED


async def test_skip_returns_the_descendant_to_pending_when_it_stopped_without_an_agent(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph = Graph(
        name="demo",
        nodes=[
            GraphNode(id="A"),
            GraphNode(id="B", depends_on=("A",)),
            GraphNode(id="D", depends_on=("B",)),
            GraphNode(id="F", depends_on=("B",)),
            GraphNode(id="E"),
        ],
    )
    started_agent = NodeAgent(id="agent-D", name="claude", node_id="D")
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.ERRORED)
    node_repo.get_nodes_by_ids.return_value = [
        build_node("B", NodeState.NEEDS_HUMAN),
        build_node("D", NodeState.NEEDS_HUMAN, agent=started_agent),
        build_node("F", NodeState.PENDING),
    ]
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = graph
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=graph_builder,
    )

    pending_node_ids = await service.skip(COMMAND, NOW)

    assert pending_node_ids == ["B"]
    node_repo.get_nodes_by_ids.assert_awaited_once_with(["B", "D", "F"])
    node_repo.update_state.assert_any_await("B", NodeState.PENDING, NOW)
    assert node_repo.update_state.await_count == 2


async def test_skip_refuses_the_node_when_the_run_does_not_have_it(
    mocker: MockerFixture,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = None
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
    )

    with pytest.raises(SkipRefused, match="A is not a node of this run"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()


async def test_skip_refuses_the_node_when_it_is_in_progress(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.IN_PROGRESS)
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
    )

    with pytest.raises(SkipRefused, match="A is in progress and cannot be skipped"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()


async def test_skip_refuses_the_node_when_it_has_merged(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.MERGED)
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
    )

    with pytest.raises(SkipRefused, match="A has merged and cannot be skipped"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()

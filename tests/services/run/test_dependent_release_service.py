from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.run.dependent_release_service import (
    DependentReleaseService,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 9, 7, tzinfo=UTC)
UPSTREAM_STOPPED_NOTE = "upstream node A stopped, so this one can never start"


async def test_release_returns_transitive_dependents_to_pending_when_an_upstream_node_stops(
    mocker: MockerFixture,
) -> None:
    graph_nodes = [
        GraphNode(id="A"),
        GraphNode(id="B", depends_on=("A",)),
        GraphNode(id="C", depends_on=("B",)),
        GraphNode(id="D"),
    ]

    graph = Graph(name="demo", nodes=graph_nodes)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [
        Node(id=node_id, state=NodeState.NEEDS_HUMAN.value) for node_id in ["B", "C"]
    ]

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [
        AuditEntry(
            node_id=node_id,
            state=NodeState.NEEDS_HUMAN.value,
            note=f"upstream node {upstream_id} stopped, so this one can never start",
            created_at=NOW,
        )
        for node_id, upstream_id in [("B", "A"), ("C", "B"), ("D", "A")]
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    service = DependentReleaseService(
        graph=graph,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
    )

    released_node_ids = await service.release("A", NOW)

    assert released_node_ids == ["B", "C"]
    node_repo.get_nodes_by_ids.assert_awaited_once_with(["B", "C"])
    assert node_repo.update_state.await_args_list == [
        mocker.call("B", NodeState.PENDING, NOW),
        mocker.call("C", NodeState.PENDING, NOW),
    ]

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    assert [
        (entry.node_id, entry.state, entry.note, entry.created_at)
        for entry in audit_entries
    ] == [
        (node_id, NodeState.PENDING.value, "an upstream node was skipped", NOW)
        for node_id in ["B", "C"]
    ]

    node_events = [
        call.args[0] for call in notification_publisher.publish.call_args_list
    ]

    assert [(event.node_id, event.type, event.created_at) for event in node_events] == [
        (node_id, NotificationType.RETRIED, NOW) for node_id in ["B", "C"]
    ]


@pytest.mark.parametrize(
    ("state", "has_agent", "note"),
    [
        (NodeState.NEEDS_HUMAN, True, UPSTREAM_STOPPED_NOTE),
        (NodeState.PENDING, False, UPSTREAM_STOPPED_NOTE),
        (NodeState.NEEDS_HUMAN, False, "executor missing is not registered"),
        (NodeState.NEEDS_HUMAN, False, None),
    ],
)
async def test_release_changes_nothing_when_the_dependent_is_not_parked_without_an_agent(
    state: NodeState, has_agent: bool, note: str | None, mocker: MockerFixture
) -> None:
    graph_nodes = [GraphNode(id="A"), GraphNode(id="B", depends_on=("A",))]
    graph = Graph(name="demo", nodes=graph_nodes)

    agent = NodeAgent(id="agent-B", node_id="B") if has_agent else None
    node = Node(id="B", state=state.value, agent=agent)

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [node]

    notes = [UPSTREAM_STOPPED_NOTE, note] if note is not None else []
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [
        AuditEntry(node_id="B", state=state.value, note=node_note, created_at=NOW)
        for node_note in notes
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    service = DependentReleaseService(
        graph=graph,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
    )

    released_node_ids = await service.release("A", NOW)

    assert released_node_ids == []
    node_repo.update_state.assert_not_awaited()
    audit_entry_repo.save.assert_not_awaited()
    notification_publisher.publish.assert_not_called()

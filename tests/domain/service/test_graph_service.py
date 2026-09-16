from datetime import UTC, datetime

import pytest
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.graph_service import GraphService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def build_graph() -> Graph:
    return Graph(
        name="demo",
        nodes=[
            GraphNode(id="A"),
            GraphNode(id="B", depends_on=("A",)),
            GraphNode(id="C", depends_on=("A", "B")),
        ],
    )


def build_node(node_id: str, state: NodeState) -> Node:
    return Node(id=node_id, state=state.value, created_at=NOW, updated_at=NOW)


def build_mixed_nodes() -> list[Node]:
    return [
        build_node("A", NodeState.MERGED),
        build_node("B", NodeState.PENDING),
        build_node("C", NodeState.PENDING),
    ]


def test_returns_the_nodes_in_graph_order_when_partitioning_by_state() -> None:
    service = GraphService(build_graph())
    nodes = build_mixed_nodes()

    assert [graph_node.id for graph_node in service.get_pending_nodes(nodes)] == [
        "B",
        "C",
    ]
    assert [graph_node.id for graph_node in service.get_merged_nodes(nodes)] == ["A"]
    assert service.get_in_progress_nodes(nodes) == []


def test_returns_them_in_graph_order_when_the_node_has_dependencies() -> None:
    service = GraphService(build_graph())

    dependencies = service.get_dependencies("C")

    assert [graph_node.id for graph_node in dependencies] == ["A", "B"]


@pytest.mark.parametrize("node_id", ["A", "missing"], ids=["no-deps", "unknown-node"])
def test_returns_nothing_when_the_node_has_no_dependencies(node_id: str) -> None:
    service = GraphService(build_graph())

    dependencies = service.get_dependencies(node_id)

    assert dependencies == []


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        ([NodeState.MERGED, NodeState.IN_PROGRESS, NodeState.PENDING], False),
        ([NodeState.MERGED, NodeState.NEEDS_HUMAN, NodeState.ERRORED], True),
        ([NodeState.MERGED, NodeState.SKIPPED, NodeState.ERRORED], True),
        ([], False),
    ],
    ids=["still-working", "all-terminal", "one-skipped", "no-nodes"],
)
def test_reports_complete_only_when_every_node_is_terminal(
    states: list[NodeState], expected: bool
) -> None:
    service = GraphService(build_graph())
    nodes = [
        build_node(node_id, state)
        for node_id, state in zip("ABC", states, strict=False)
    ]

    assert service.is_complete(nodes) is expected

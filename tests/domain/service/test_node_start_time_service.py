from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.service.node_start_time_service import (
    NodeStartTimeService,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)

pytestmark = pytest.mark.unit

BuildNode = Callable[[str, NodeState, datetime], Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id, state, updated_at: Node(
        id=node_id, state=state.value, created_at=updated_at, updated_at=updated_at
    )


def test_get_start_time_returns_none_when_the_node_has_no_cooldown(
    build_node: BuildNode,
) -> None:
    dependency = GraphNode(id="A")
    graph_node = GraphNode(id="B", depends_on=("A",))
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    nodes = [build_node("A", NodeState.MERGED, datetime(2026, 9, 26, tzinfo=UTC))]

    start_time = NodeStartTimeService(graph).get_start_time(graph_node, nodes)

    assert start_time is None


def test_get_start_time_returns_none_when_no_dependency_is_merged_or_skipped(
    build_node: BuildNode,
) -> None:
    dependency = GraphNode(id="A")
    graph_node = GraphNode(id="B", depends_on=("A",), cooldown_seconds=3600)
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    nodes = [build_node("A", NodeState.RESTING, datetime(2026, 9, 26, tzinfo=UTC))]

    start_time = NodeStartTimeService(graph).get_start_time(graph_node, nodes)

    assert start_time is None


@pytest.mark.parametrize(
    ("skipped_at", "merged_at"),
    [
        (datetime(2026, 9, 26, tzinfo=UTC), datetime(2026, 9, 19, tzinfo=UTC)),
        (datetime(2026, 9, 19, tzinfo=UTC), datetime(2026, 9, 26, tzinfo=UTC)),
    ],
    ids=["skip_is_newer", "inherited_merge_is_newer"],
)
def test_get_start_time_uses_the_latest_merged_or_skipped_dependency_update_when_a_dependency_is_skipped(
    skipped_at: datetime, merged_at: datetime, build_node: BuildNode
) -> None:
    root = GraphNode(id="A")
    skipped_dependency = GraphNode(id="B", depends_on=("A",))
    graph_node = GraphNode(id="C", depends_on=("B",), cooldown_seconds=3600)
    graph = Graph(name="demo", nodes=[root, skipped_dependency, graph_node])

    nodes = [
        build_node("A", NodeState.MERGED, merged_at),
        build_node("B", NodeState.SKIPPED, skipped_at),
    ]

    start_time = NodeStartTimeService(graph).get_start_time(graph_node, nodes)

    assert start_time == datetime(2026, 9, 26, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("cooldown_seconds", "resume_hours", "start_hours"),
    [(0, 2, 2), (3600, 2, 2), (10800, 2, 3), (3600, 1, 1)],
    ids=["no_cooldown", "resume_is_later", "cooldown_is_later", "same_time"],
)
def test_get_start_time_returns_the_later_resume_or_cooldown_time_when_the_node_has_a_resume_time(
    cooldown_seconds: int,
    resume_hours: int,
    start_hours: int,
    build_node: BuildNode,
) -> None:
    merged_at = datetime(2026, 9, 26, tzinfo=UTC)
    resume_at = merged_at + timedelta(hours=resume_hours)

    dependency = GraphNode(id="A")
    graph_node = GraphNode(id="B", depends_on=("A",), cooldown_seconds=cooldown_seconds)
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node = Node(id="B", state=NodeState.PENDING.value, resume_at=resume_at)
    dependency_node = build_node("A", NodeState.MERGED, merged_at)
    nodes = [dependency_node, node]

    service = NodeStartTimeService(graph)

    start_time = service.get_start_time(graph_node, nodes)

    assert start_time == merged_at + timedelta(hours=start_hours)

import pytest
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.service.graph_validation_service import (
    GraphValidationService,
)
from virgo_agentic_dag.domain.service.validators.cycle_validator import CycleValidator
from virgo_agentic_dag.domain.service.validators.duplicate_node_validator import (
    DuplicateNodeValidator,
)
from virgo_agentic_dag.domain.service.validators.missing_dependency_validator import (
    MissingDependencyValidator,
)
from virgo_agentic_dag.domain.service.validators.missing_executor_validator import (
    MissingExecutorValidator,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent

pytestmark = pytest.mark.unit


def build_service() -> GraphValidationService:
    return GraphValidationService(
        [
            CycleValidator(),
            DuplicateNodeValidator(),
            MissingDependencyValidator(),
            MissingExecutorValidator(),
        ]
    )


def build_node(node_id: str, depends_on: tuple[str, ...] = ()) -> GraphNode:
    return GraphNode(
        id=node_id, depends_on=depends_on, executor_agent=ExecutorAgent.CLAUDE
    )


def test_reports_nothing_when_the_graph_is_clean() -> None:
    service = build_service()
    graph = Graph(name="demo", nodes=[build_node("A"), build_node("B", ("A",))])

    result = service.validate_graph(graph)

    assert result.errors == []
    assert not result.is_blocking()


def test_blocks_when_a_dependency_is_not_in_the_graph() -> None:
    service = build_service()
    graph = Graph(name="demo", nodes=[build_node("A", ("ghost",))])

    result = service.validate_graph(graph)

    assert result.is_blocking()
    assert result.errors[0].code == "unknown-dependency"


def test_blocks_when_a_node_id_is_declared_twice() -> None:
    service = build_service()
    graph = Graph(name="demo", nodes=[build_node("A"), build_node("A")])

    result = service.validate_graph(graph)

    assert result.is_blocking()
    assert result.errors[0].code == "duplicate-node"


def test_blocks_when_a_node_resolves_to_no_executor() -> None:
    service = build_service()
    graph = Graph(name="demo", nodes=[GraphNode(id="A")])

    result = service.validate_graph(graph)

    assert result.is_blocking()
    assert result.errors[0].code == "missing-executor"


def test_names_only_the_members_when_a_cycle_is_found() -> None:
    service = build_service()
    graph = Graph(
        name="demo",
        nodes=[
            build_node("A", ("B",)),
            build_node("B", ("A",)),
            build_node("C"),
        ],
    )

    result = service.validate_graph(graph)

    assert result.errors[0].code == "dependency-cycle"
    assert "A, B" in result.errors[0].message
    assert "C" not in result.errors[0].message

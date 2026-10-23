from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
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
from virgo_agentic_dag.domain.service.validators.missing_project_root_validator import (
    MissingProjectRootValidator,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec

pytestmark = pytest.mark.unit


def build_service() -> GraphValidationService:
    return GraphValidationService(
        [
            CycleValidator(),
            DuplicateNodeValidator(),
            MissingDependencyValidator(),
            MissingExecutorValidator(),
            MissingProjectRootValidator(),
        ]
    )


def build_node(node_id: str, depends_on: tuple[str, ...] = ()) -> GraphNode:
    return GraphNode(
        id=node_id, depends_on=depends_on, executor_agent=ExecutorAgent.CLAUDE
    )


def test_reports_nothing_when_the_graph_is_clean() -> None:
    service = build_service()
    graph = Graph(
        name="demo",
        nodes=[build_node("A"), build_node("B", ("A",))],
        project_root=Path("/projects/demo"),
    )

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


@pytest.mark.parametrize("project_root", [None, Path("/projects/demo")])
@pytest.mark.parametrize("node_project_root", [None, Path("/projects/node")])
def test_validation_blocks_when_the_dag_has_no_project_root(
    mocker: MockerFixture,
    project_root: Path | None,
    node_project_root: Path | None,
) -> None:
    node_spec = NodeSpec(id="A", project_root=node_project_root)
    dag_spec = DagSpec(name="demo", nodes=(node_spec,), project_root=project_root)

    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = dag_spec

    graph_builder = GraphBuilder(dag_loader=dag_loader)
    dag_path = Path("dag.toml")
    graph = graph_builder.build_from_path(dag_path)

    service = build_service()

    validation_result = service.validate_graph(graph)

    assert graph.nodes[0].project_root == (node_project_root or project_root)
    assert validation_result.is_blocking() is (project_root is None)
    if project_root is None:
        assert validation_result.errors[0].code == "missing-project-root"

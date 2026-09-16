from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.specs.dag_spec import (
    DEFAULT_BASE_BRANCH,
    WORKSPACE_HOME,
    DagSpec,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget

pytestmark = pytest.mark.unit

DAG_PATH = Path("dag.toml")


def test_mirrors_the_spec_when_building_the_graph(mocker: MockerFixture) -> None:
    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(
        name="demo",
        nodes=(
            NodeSpec(id="A", instructions="first"),
            NodeSpec(id="B", instructions="second", depends_on=("A",)),
        ),
    )

    builder = GraphBuilder(dag_loader=dag_loader)

    graph = builder.build_from_path(DAG_PATH)

    assert graph.name == "demo"
    assert [node.id for node in graph.nodes] == ["A", "B"]
    assert graph.nodes[1].depends_on == ("A",)


@pytest.mark.parametrize(
    ("index", "expected_name"), [(0, "A"), (1, "Vesta")], ids=["unnamed", "named"]
)
def test_falls_back_to_the_node_id_when_the_spec_names_no_agent(
    index: int, expected_name: str, mocker: MockerFixture
) -> None:
    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(
        name="demo", nodes=(NodeSpec(id="A"), NodeSpec(id="B", name="Vesta"))
    )

    builder = GraphBuilder(dag_loader=dag_loader)

    graph = builder.build_from_path(DAG_PATH)

    assert graph.nodes[index].get_agent_name() == expected_name


def test_takes_the_dag_defaults_when_the_node_names_nothing(
    mocker: MockerFixture,
) -> None:
    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(
        name="demo",
        project_root=Path("/projects/virgo"),
        workspace_path=Path("/ws/virgo"),
        executor_agent=ExecutorAgent.CLAUDE,
        base_branch="develop",
        caps=AttemptBudget(node_recoveries=5),
        nodes=(NodeSpec(id="A"),),
    )

    builder = GraphBuilder(dag_loader=dag_loader)

    node = builder.build_from_path(DAG_PATH).nodes[0]

    assert node.project_root == Path("/projects/virgo")
    assert node.workspace_path == Path("/ws/virgo")
    assert node.executor_agent is ExecutorAgent.CLAUDE
    assert node.base_branch == "develop"
    assert node.recovery_attempts_allowed == 5


def test_takes_the_node_values_when_the_node_names_its_own(
    mocker: MockerFixture,
) -> None:
    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(
        name="demo",
        project_root=Path("/projects/virgo"),
        workspace_path=Path("/ws/virgo"),
        base_branch="develop",
        nodes=(
            NodeSpec(
                id="A",
                project_root=Path("/projects/spacy"),
                workspace_path=Path("/ws/spacy"),
                base_branch="main",
            ),
        ),
    )

    builder = GraphBuilder(dag_loader=dag_loader)

    node = builder.build_from_path(DAG_PATH).nodes[0]

    assert node.project_root == Path("/projects/spacy")
    assert node.workspace_path == Path("/ws/spacy")
    assert node.base_branch == "main"


def test_falls_back_to_the_package_defaults_when_the_dag_names_nothing(
    mocker: MockerFixture,
) -> None:
    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(name="bare", nodes=(NodeSpec(id="A"),))

    builder = GraphBuilder(dag_loader=dag_loader)

    node = builder.build_from_path(DAG_PATH).nodes[0]

    assert node.project_root == Path.cwd()
    assert node.workspace_path == WORKSPACE_HOME / "bare"
    assert node.base_branch == DEFAULT_BASE_BRANCH
    assert node.executor_agent is ExecutorAgent.CLAUDE

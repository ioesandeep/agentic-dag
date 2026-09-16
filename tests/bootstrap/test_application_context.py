import io
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.application_context import ApplicationContext
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec

pytestmark = pytest.mark.unit

DAG_PATH = Path("dag.toml")


class Greeter:
    """A bean the container has no interface for, so the tests have a type to key on."""

    def __init__(self, greeting: str) -> None:
        self.greeting = greeting


def test_returns_the_same_instance_when_a_bean_is_asked_for_twice(
    mocker: MockerFixture,
) -> None:
    context = ApplicationContext(TickCommand(dag_path=DAG_PATH), io.StringIO())
    build_greeter = mocker.MagicMock(return_value=Greeter("hello"))
    context.register(Greeter, build_greeter)

    greeter = context.get(Greeter)

    assert context.get(Greeter) is greeter
    build_greeter.assert_called_once_with(context)


def test_raises_when_the_bean_was_never_registered() -> None:
    context = ApplicationContext(TickCommand(dag_path=DAG_PATH), io.StringIO())

    with pytest.raises(LookupError, match="Greeter"):
        context.get(Greeter)


def test_writes_through_when_emitting() -> None:
    output = io.StringIO()
    context = ApplicationContext(TickCommand(dag_path=DAG_PATH), output)

    context.emit("hello\n")

    assert output.getvalue() == "hello\n"


def test_uses_the_given_path_when_the_graph_names_a_database() -> None:
    context = ApplicationContext(TickCommand(dag_path=DAG_PATH), io.StringIO())
    context.register(
        DagSpec,
        lambda _: DagSpec(
            name="demo", nodes=(NodeSpec(id="A"),), db_path=Path("/runs/x.sqlite3")
        ),
    )

    assert context.get_db_path() == Path("/runs/x.sqlite3")


def test_falls_back_to_the_run_home_when_no_database_is_named() -> None:
    context = ApplicationContext(TickCommand(dag_path=DAG_PATH), io.StringIO())
    context.register(DagSpec, lambda _: DagSpec(name="demo", nodes=(NodeSpec(id="A"),)))

    assert context.get_db_path() == Path.home() / ".virgo-dag" / "demo" / "db.sqlite3"


def test_derives_the_database_from_the_name_when_the_command_carries_one() -> None:
    context = ApplicationContext(AbortCommand(dag_name="demo"), io.StringIO())

    assert context.get_db_path() == Path.home() / ".virgo-dag" / "demo" / "db.sqlite3"

import io
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.bootstrap.application_context import ApplicationContext
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.command.command import Command
from virgo_agentic_dag.domain.command.log_command import LogCommand
from virgo_agentic_dag.domain.command.status_command import StatusCommand
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

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


@pytest.mark.parametrize("has_dag_file", [False, True])
def test_context_uses_the_default_database_when_the_named_run_has_no_custom_path(
    mocker: MockerFixture, tmp_path: Path, has_dag_file: bool
) -> None:
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    db_path = tmp_path / "demo" / "db.sqlite3"
    dag_path = tmp_path / "demo" / "dag.toml"

    existing_paths = [db_path, dag_path] if has_dag_file else [db_path]
    mocker.patch.object(
        Path, "is_file", autospec=True, side_effect=lambda path: path in existing_paths
    )

    dag_loader = mocker.MagicMock(spec=TomlDagLoader)
    dag_loader.get_db_path.return_value = None

    command = AbortCommand(dag_name="demo")

    output_writer = io.StringIO()
    context = ApplicationContext(command=command, output_writer=output_writer)
    context.register(TomlDagLoader, lambda _: dag_loader)

    resolved_db_path = context.get_db_path()

    assert resolved_db_path == db_path


@pytest.mark.parametrize(
    "command_type", [AbortCommand, WatchCommand, StatusCommand, LogCommand]
)
def test_context_uses_the_saved_custom_database_when_the_command_specifies_a_name(
    mocker: MockerFixture, tmp_path: Path, command_type: type[Command]
) -> None:
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    dag_path = tmp_path / "demo" / "dag.toml"
    db_path = tmp_path / "custom" / "run.sqlite3"

    existing_paths = [dag_path, db_path]
    mocker.patch.object(
        Path, "is_file", autospec=True, side_effect=lambda path: path in existing_paths
    )

    dag_loader = mocker.MagicMock(spec=TomlDagLoader)
    dag_loader.get_db_path.return_value = db_path

    command = command_type(dag_name="demo")

    output_writer = io.StringIO()
    context = ApplicationContext(command=command, output_writer=output_writer)
    context.register(TomlDagLoader, lambda _: dag_loader)

    resolved_db_path = context.get_db_path()

    assert resolved_db_path == db_path


def test_context_raises_when_the_saved_custom_database_does_not_exist(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    dag_path = tmp_path / "demo" / "dag.toml"
    default_db_path = tmp_path / "demo" / "db.sqlite3"

    existing_paths = [dag_path, default_db_path]
    mocker.patch.object(
        Path, "is_file", autospec=True, side_effect=lambda path: path in existing_paths
    )

    db_path = tmp_path / "custom" / "missing.sqlite3"
    dag_loader = mocker.MagicMock(spec=TomlDagLoader)
    dag_loader.get_db_path.return_value = db_path

    command = AbortCommand(dag_name="demo")

    output_writer = io.StringIO()
    context = ApplicationContext(command=command, output_writer=output_writer)
    context.register(TomlDagLoader, lambda _: dag_loader)

    with pytest.raises(ConfigError, match="no dag named demo"):
        context.get_db_path()

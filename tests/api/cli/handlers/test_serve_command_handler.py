import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.serve_command_handler import ServeCommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.serve_command import ServeCommand
from virgo_agentic_dag.domain.infra.web.web_server import WebServer
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)

pytestmark = pytest.mark.unit


async def test_serves_on_loopback_when_the_command_names_no_address(
    mocker: MockerFixture,
) -> None:
    web_server = mocker.MagicMock(spec=WebServer)
    database_registry = mocker.MagicMock(spec=DagDatabaseRegistry)
    handler = ServeCommandHandler(
        web_server=web_server, database_registry=database_registry
    )
    command = ServeCommand()

    exit_code = await handler.handle(command)

    assert exit_code is ExitCode.SUCCESS
    web_server.serve.assert_awaited_once_with("127.0.0.1", 8788)


async def test_serves_on_the_address_the_command_names(mocker: MockerFixture) -> None:
    web_server = mocker.MagicMock(spec=WebServer)
    database_registry = mocker.MagicMock(spec=DagDatabaseRegistry)
    handler = ServeCommandHandler(
        web_server=web_server, database_registry=database_registry
    )
    command = ServeCommand(host="0.0.0.0", port=9000)

    await handler.handle(command)

    web_server.serve.assert_awaited_once_with("0.0.0.0", 9000)


async def test_closes_every_dag_database_when_the_server_stops(
    mocker: MockerFixture,
) -> None:
    web_server = mocker.MagicMock(spec=WebServer)
    database_registry = mocker.MagicMock(spec=DagDatabaseRegistry)
    handler = ServeCommandHandler(
        web_server=web_server, database_registry=database_registry
    )
    command = ServeCommand()

    await handler.handle(command)

    database_registry.dispose.assert_awaited_once_with()

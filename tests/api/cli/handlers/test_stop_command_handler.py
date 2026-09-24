import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.stop_command_handler import StopCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.stop_command import StopCommand
from virgo_agentic_dag.domain.exceptions.run.stop_refused import StopRefused
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.services.stop.node_stop_service import NodeStopService

pytestmark = pytest.mark.unit

COMMAND = StopCommand(dag_path=Path("dag.toml"), node_id="TOKENS")


@pytest.fixture
def out() -> Iterator[io.StringIO]:
    out = io.StringIO()
    token = bind_context(ApplicationContext(COMMAND, out))

    yield out

    unbind_context(token)


async def test_stop_command_handler_prints_node_stopped_label_when_stop_succeeds(
    mocker: MockerFixture, out: io.StringIO
) -> None:
    handler = StopCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        node_stop_service=mocker.MagicMock(spec=NodeStopService),
    )

    exit_code = await handler.handle(COMMAND)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == "stop moves TOKENS to needs human\n"


async def test_stop_command_handler_releases_the_run_lock_when_the_stop_service_raises_stop_refused(
    mocker: MockerFixture, out: io.StringIO
) -> None:
    node_stop_service = mocker.MagicMock(spec=NodeStopService)
    node_stop_service.stop.side_effect = StopRefused(
        "stop fails for TOKENS because its state is resting\n"
    )
    run_lock = mocker.MagicMock(spec=RunLock)
    handler = StopCommandHandler(run_lock=run_lock, node_stop_service=node_stop_service)

    exit_code = await handler.handle(COMMAND)

    assert exit_code is ExitCode.FAILURE
    assert out.getvalue() == "stop fails for TOKENS because its state is resting\n"
    run_lock.release.assert_called_once()

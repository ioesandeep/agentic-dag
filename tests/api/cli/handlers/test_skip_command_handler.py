import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.skip_command_handler import SkipCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.services.run.node_skip_service import NodeSkipService

pytestmark = pytest.mark.unit

COMMAND = SkipCommand(dag_path=Path("dag.toml"), node_id="TOKENS")


@pytest.fixture
def out() -> Iterator[io.StringIO]:
    out = io.StringIO()
    token = bind_context(ApplicationContext(COMMAND, out))

    yield out

    unbind_context(token)


async def test_skip_prints_the_skipped_node_and_each_node_returned_to_pending(
    mocker: MockerFixture, out: io.StringIO
) -> None:
    node_skip_service = mocker.MagicMock(spec=NodeSkipService)
    node_skip_service.skip.return_value = ["MIDDLEWARE"]
    handler = SkipCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock), node_skip_service=node_skip_service
    )

    exit_code = await handler.handle(COMMAND)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == (
        "TOKENS is skipped\n"
        "MIDDLEWARE is pending again because an upstream node was skipped\n"
    )


async def test_skip_releases_the_run_lock_when_the_node_cannot_be_skipped(
    mocker: MockerFixture, out: io.StringIO
) -> None:
    node_skip_service = mocker.MagicMock(spec=NodeSkipService)
    node_skip_service.skip.side_effect = SkipRefused(
        "TOKENS has merged and cannot be skipped\n"
    )
    run_lock = mocker.MagicMock(spec=RunLock)
    handler = SkipCommandHandler(run_lock=run_lock, node_skip_service=node_skip_service)

    exit_code = await handler.handle(COMMAND)

    assert exit_code is ExitCode.FAILURE
    assert out.getvalue() == "TOKENS has merged and cannot be skipped\n"
    run_lock.release.assert_called_once()

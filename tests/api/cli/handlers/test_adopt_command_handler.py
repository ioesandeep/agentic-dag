from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.adopt_command_handler import AdoptCommandHandler
from virgo_agentic_dag.domain.command.adopt_command import AdoptCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.services.run.adopt_service import AdoptService

pytestmark = pytest.mark.unit


@pytest.fixture
def events() -> list[str]:
    return []


@pytest.fixture
def run_lock(mocker: MockerFixture, events: list[str]) -> RunLock:
    lock = mocker.MagicMock(spec=RunLock)
    lock.acquire_waiting.side_effect = lambda: events.append("acquire_waiting")
    lock.release.side_effect = lambda: events.append("release")

    return lock


@pytest.fixture
def adopt_service(mocker: MockerFixture, events: list[str]) -> AdoptService:
    service = mocker.AsyncMock(spec=AdoptService)

    def record(command: AdoptCommand) -> ExitCode:
        events.append("adopt")

        return ExitCode.SUCCESS

    service.adopt.side_effect = record

    return service


@pytest.fixture
def handler(run_lock: RunLock, adopt_service: AdoptService) -> AdoptCommandHandler:
    return AdoptCommandHandler(run_lock, adopt_service)


async def test_handle_acquires_run_lock_around_adoption(
    handler: AdoptCommandHandler, events: list[str]
) -> None:
    exit_code = await handler.handle(AdoptCommand(dag_path=Path("dag.toml"), pr="412"))

    assert exit_code is ExitCode.SUCCESS
    assert events == ["acquire_waiting", "adopt", "release"]


async def test_handle_releases_run_lock_when_adoption_raises(
    handler: AdoptCommandHandler, adopt_service: AdoptService, events: list[str]
) -> None:
    adopt_service.adopt.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await handler.handle(AdoptCommand(dag_path=Path("dag.toml"), pr="412"))

    assert events == ["acquire_waiting", "release"]

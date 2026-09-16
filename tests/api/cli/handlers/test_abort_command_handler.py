import io
import json
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.abort_command_handler import AbortCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.infra.agent.session_killer import SessionKiller
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.services.watching.watcher_service import WatcherService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 2, tzinfo=UTC)


@pytest.fixture
def job() -> ScheduledJob:
    return ScheduledJob(
        dag_name="demo",
        label=ScheduledJob.get_label("demo"),
        argv=json.dumps(["/venv/bin/dagctl", "start"]),
        interval_seconds=300,
        working_directory="/runs/demo",
        log_path="/runs/demo/start.log",
        environment="{}",
        created_at=NOW,
    )


@pytest.fixture
def build_open_session() -> Callable[[int], AgentSession]:
    return lambda pid: AgentSession(
        id=pid, agent_id=f"agent-{pid}", started_at=NOW, pid=pid
    )


async def test_stops_the_host_waking_the_run_when_one_was_recorded(
    mocker: MockerFixture, job: ScheduledJob
) -> None:
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    handler = AbortCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        watcher_service=mocker.MagicMock(spec=WatcherService),
        session_killer=mocker.MagicMock(spec=SessionKiller),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    scheduler.retire.assert_awaited_once_with(job)
    scheduled_job_repo.delete.assert_awaited_once_with(job)


async def test_says_so_and_succeeds_when_no_host_was_waking_the_run(
    mocker: MockerFixture,
) -> None:
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    handler = AbortCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        watcher_service=mocker.MagicMock(spec=WatcherService),
        session_killer=mocker.MagicMock(spec=SessionKiller),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    scheduler.retire.assert_not_awaited()
    assert "demo" in out.getvalue()


async def test_has_every_open_session_killed_between_claiming_and_freeing(
    mocker: MockerFixture, build_open_session: Callable[[int], AgentSession]
) -> None:
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = [
        build_open_session(41),
        build_open_session(42),
    ]

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    run_lock = mocker.MagicMock(spec=RunLock)
    watcher_service = mocker.MagicMock(spec=WatcherService)
    session_killer = mocker.MagicMock(spec=SessionKiller)

    call_order = mocker.MagicMock()
    call_order.attach_mock(run_lock.acquire_waiting, "acquire_waiting")
    call_order.attach_mock(watcher_service.stop, "stop_watcher")
    call_order.attach_mock(session_killer.kill, "kill_session")
    call_order.attach_mock(run_lock.release, "release")

    handler = AbortCommandHandler(
        run_lock=run_lock,
        watcher_service=watcher_service,
        session_killer=session_killer,
        agent_session_repo=agent_session_repo,
        scheduler_factory=mocker.MagicMock(spec=SchedulerFactory),
        scheduled_job_repo=scheduled_job_repo,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    assert [name for name, _, _ in call_order.mock_calls] == [
        "acquire_waiting",
        "stop_watcher",
        "kill_session",
        "kill_session",
        "release",
    ]
    assert [call.args[0].pid for call in session_killer.kill.await_args_list] == [
        41,
        42,
    ]


async def test_lets_go_of_the_run_when_the_sweep_fails(mocker: MockerFixture) -> None:
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.side_effect = RuntimeError("boom")

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    run_lock = mocker.MagicMock(spec=RunLock)
    watcher_service = mocker.MagicMock(spec=WatcherService)

    call_order = mocker.MagicMock()
    call_order.attach_mock(run_lock.acquire_waiting, "acquire_waiting")
    call_order.attach_mock(watcher_service.stop, "stop_watcher")
    call_order.attach_mock(run_lock.release, "release")

    handler = AbortCommandHandler(
        run_lock=run_lock,
        watcher_service=watcher_service,
        session_killer=mocker.MagicMock(spec=SessionKiller),
        agent_session_repo=agent_session_repo,
        scheduler_factory=mocker.MagicMock(spec=SchedulerFactory),
        scheduled_job_repo=scheduled_job_repo,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)

    with pytest.raises(RuntimeError, match="boom"):
        try:
            await handler.handle(command)
        finally:
            unbind_context(token)

    assert [name for name, _, _ in call_order.mock_calls] == [
        "acquire_waiting",
        "stop_watcher",
        "release",
    ]

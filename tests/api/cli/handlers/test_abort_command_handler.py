import io
import json
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

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
from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller
from virgo_agentic_dag.domain.infra.agent.session_killer import SessionKiller
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.infra.agent.process_group_killer import ProcessGroupKiller
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.recovery.recovery_session_killer import (
    RecoverySessionKiller,
)
from virgo_agentic_dag.services.watching.watcher_service import WatcherService

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


@pytest.mark.unit
async def test_stops_the_host_waking_the_run_when_one_was_recorded(
    mocker: MockerFixture, job: ScheduledJob
) -> None:
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.get_session_pid.return_value = None

    handler = AbortCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        watcher_service=mocker.MagicMock(spec=WatcherService),
        session_killer=mocker.MagicMock(spec=SessionKiller),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        recovery_session_repo=recovery_session_repo,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        extraction_lock=extraction_lock,
        process_killer=mocker.MagicMock(spec=ProcessKiller),
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


@pytest.mark.unit
async def test_says_so_and_succeeds_when_no_host_was_waking_the_run(
    mocker: MockerFixture,
) -> None:
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.get_session_pid.return_value = None

    handler = AbortCommandHandler(
        run_lock=mocker.MagicMock(spec=RunLock),
        watcher_service=mocker.MagicMock(spec=WatcherService),
        session_killer=mocker.MagicMock(spec=SessionKiller),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        recovery_session_repo=recovery_session_repo,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        extraction_lock=extraction_lock,
        process_killer=mocker.MagicMock(spec=ProcessKiller),
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


@pytest.mark.parametrize("has_background_sessions", [False, True])
@pytest.mark.integration
async def test_abort_kills_open_sessions_before_releasing_the_run_lock(
    mocker: MockerFixture,
    build_open_session: Callable[[int], AgentSession],
    has_background_sessions: bool,
    tmp_path: Path,
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

    recovery_process = subprocess.Popen(["sleep", "30"], start_new_session=True)
    learning_process = subprocess.Popen(["sleep", "30"], start_new_session=True)

    recovery_session = RecoverySession(
        id=1,
        session_token="token-1",
        pid=recovery_process.pid,
        started_at=NOW,
        node_ids='["A"]',
    )
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = (
        recovery_session if has_background_sessions else None
    )

    process_killer = ProcessGroupKiller()
    recovery_session_killer = RecoverySessionKiller(
        recovery_session_repo=recovery_session_repo, process_killer=process_killer
    )

    lock_path = tmp_path / "learning_extraction.lock"
    extraction_lock = ExtractionLock(lock_path)
    if has_background_sessions:
        extraction_lock.record_session_pid(learning_process.pid)

    kill_process_group = mocker.patch("os.killpg", wraps=os.killpg)

    call_order = mocker.MagicMock()
    call_order.attach_mock(run_lock.acquire_waiting, "acquire_waiting")
    call_order.attach_mock(watcher_service.stop, "stop_watcher")
    call_order.attach_mock(session_killer.kill, "kill_session")
    call_order.attach_mock(kill_process_group, "kill_process_group")
    call_order.attach_mock(recovery_session_repo.close, "close_recovery_session")
    call_order.attach_mock(run_lock.release, "release")

    handler = AbortCommandHandler(
        run_lock=run_lock,
        watcher_service=watcher_service,
        session_killer=session_killer,
        agent_session_repo=agent_session_repo,
        scheduler_factory=mocker.MagicMock(spec=SchedulerFactory),
        scheduled_job_repo=scheduled_job_repo,
        recovery_session_repo=recovery_session_repo,
        recovery_session_killer=recovery_session_killer,
        extraction_lock=extraction_lock,
        process_killer=process_killer,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
        if has_background_sessions:
            recovery_process.wait(timeout=5)
            learning_process.wait(timeout=5)
    finally:
        unbind_context(token)
        recovery_process.kill()
        learning_process.kill()
        recovery_process.wait(timeout=5)
        learning_process.wait(timeout=5)

    expected_calls = [
        "acquire_waiting",
        "stop_watcher",
        "kill_session",
        "kill_session",
    ]
    if has_background_sessions:
        expected_calls.extend(
            ["kill_process_group", "close_recovery_session", "kill_process_group"]
        )

    expected_calls.append("release")

    assert exit_code is ExitCode.SUCCESS
    assert [name for name, _, _ in call_order.mock_calls] == expected_calls
    assert [call.args[0].pid for call in session_killer.kill.await_args_list] == [
        41,
        42,
    ]

    if has_background_sessions:
        current_time = session_killer.kill.await_args_list[0].args[1]
        closed_recovery_session = recovery_session_repo.close.await_args.args[0]

        assert closed_recovery_session.ended_at == current_time
        assert recovery_process.returncode == -9
        assert learning_process.returncode == -9
    else:
        recovery_session_repo.close.assert_not_awaited()
        kill_process_group.assert_not_called()

    assert extraction_lock.is_free() is True


@pytest.mark.unit
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
        recovery_session_repo=mocker.MagicMock(spec=RecoverySessionRepo),
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        extraction_lock=mocker.MagicMock(spec=ExtractionLock),
        process_killer=mocker.MagicMock(spec=ProcessKiller),
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

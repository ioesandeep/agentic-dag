import asyncio
import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.infra.scheduling.systemd_retirement import (
    lock_units,
    retire_service,
)
from virgo_agentic_dag.infra.scheduling.systemd_scheduler import SystemdScheduler
from virgo_agentic_dag.infra.scheduling.systemd_unit import SystemdUnit

pytestmark = pytest.mark.unit


@pytest.fixture
def get_job(tmp_path: Path) -> Callable[..., ScheduledJob]:
    environment = {"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    environment_json = json.dumps(environment)
    created_at = datetime(2026, 10, 13, tzinfo=UTC)
    job_values = {
        "dag_name": "demo",
        "label": "fyi.virgo.dag.demo",
        "argv": '["/venv/bin/dagctl", "start"]',
        "interval_seconds": 5,
        "working_directory": str(tmp_path),
        "log_path": str(tmp_path / "start.log"),
        "environment": environment_json,
        "created_at": created_at,
    }

    return lambda **changes: ScheduledJob(**(job_values | changes))


@pytest.mark.parametrize("label", ["fyi.virgo.dag.demo", "fyi.virgo.dag.demo space %"])
async def test_retirement_defers_service_removal_without_waiting_for_its_exit(
    label: str, get_job: Callable[..., ScheduledJob], mocker: MockerFixture
) -> None:
    job = get_job(label=label)
    unit_files = SystemdUnit.list_for_job(job)
    service_path = unit_files[0].path
    timer_path = unit_files[1].path
    service_path.parent.mkdir(parents=True)
    service_path.write_text("service")
    timer_path.write_text("timer")
    command_runner = mocker.MagicMock(spec=CommandRunner)
    present = RunResult(returncode=0, stdout="LoadState=loaded\nActiveState=active\n")
    enabled = RunResult(returncode=0, stdout="enabled\n")
    success = RunResult(returncode=0)
    command_runner.run.side_effect = [present, enabled] * 2 + [success] * 3

    scheduler = SystemdScheduler(command_runner=command_runner)

    await scheduler.retire(job)

    assert service_path.read_text() == "service"
    assert not timer_path.exists()
    command_runner.run.assert_any_call(
        ["systemctl", "--user", "stop", "--no-block", "--", timer_path.name]
    )

    command_runner.run.assert_any_call(
        ["systemctl", "--user", "disable", "--no-reload", "--", timer_path.name]
    )

    commands = [call.args[0] for call in command_runner.run.call_args_list]
    cleanup_command = commands[-1]
    assert cleanup_command[:5] == [
        "systemd-run",
        "--user",
        "--collect",
        "--no-block",
        "--expand-environment=no",
    ]

    service_name = service_path.name.replace("\\", "\\\\")
    assert "--property=After=" + service_name in cleanup_command
    assert cleanup_command[-1] == str(service_path)


def test_cleanup_removes_retired_service_and_is_repeatable(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    service_path = tmp_path / "demo.service"
    service_path.write_text("service")
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)
    mocker.patch(
        "virgo_agentic_dag.infra.scheduling.systemd_retirement.SubprocessCommandRunner",
        return_value=command_runner,
    )

    retire_service(service_path)
    retire_service(service_path)

    assert not service_path.exists()
    commands = [call.args[0] for call in command_runner.run.call_args_list]
    assert commands == [
        ["systemctl", "--user", "disable", "--no-reload", "--", "demo.service"],
        ["systemctl", "--user", "daemon-reload"],
    ]


async def test_cleanup_waits_for_registration_and_preserves_new_units(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    service_path = tmp_path / "demo.service"
    timer_path = tmp_path / "demo.timer"
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)
    mocker.patch(
        "virgo_agentic_dag.infra.scheduling.systemd_retirement.SubprocessCommandRunner",
        return_value=command_runner,
    )

    cleanup_task: asyncio.Task[None] | None = None
    try:
        async with lock_units(service_path):
            service_path.write_text("new service")
            cleanup = asyncio.to_thread(retire_service, service_path)
            cleanup_task = asyncio.create_task(cleanup)
            pending_cleanup = asyncio.shield(cleanup_task)
            with pytest.raises(TimeoutError, match="^$"):
                await asyncio.wait_for(pending_cleanup, timeout=0.2)

            timer_path.write_text("new timer")
    finally:
        if cleanup_task is not None:
            await asyncio.wait_for(cleanup_task, timeout=3)

    assert service_path.read_text() == "new service"
    assert timer_path.read_text() == "new timer"
    command_runner.run.assert_not_called()


async def test_registration_waits_for_cleanup_before_replacing_service(
    get_job: Callable[..., ScheduledJob], mocker: MockerFixture
) -> None:
    job = get_job()
    unit_files = SystemdUnit.list_for_job(job)
    service_path = unit_files[0].path
    command_runner = mocker.MagicMock(spec=CommandRunner)
    missing = RunResult(returncode=1, stdout="LoadState=not-found\n")
    not_enabled = RunResult(returncode=4, stdout="not-found\n")
    success = RunResult(returncode=0)
    command_runner.run.side_effect = [missing, not_enabled] * 2 + [success] * 3

    scheduler = SystemdScheduler(command_runner=command_runner)

    registration_task: asyncio.Task[None] | None = None
    try:
        async with lock_units(service_path):
            service_path.write_text("previous service")
            registration = scheduler.register(job)
            registration_task = asyncio.create_task(registration)
            pending_registration = asyncio.shield(registration_task)
            with pytest.raises(TimeoutError, match="^$"):
                await asyncio.wait_for(pending_registration, timeout=0.2)

            assert service_path.read_text() == "previous service"
            command_runner.run.assert_not_called()
    finally:
        if registration_task is not None:
            await asyncio.wait_for(registration_task, timeout=3)

    assert service_path.read_bytes() == unit_files[0].content
    assert unit_files[1].path.read_bytes() == unit_files[1].content


@pytest.mark.parametrize("failure", ["bus", "executable", "timeout"])
def test_cleanup_failure_keeps_service_for_retry(
    failure: str, tmp_path: Path, mocker: MockerFixture
) -> None:
    service_path = tmp_path / "demo.service"
    service_path.write_text("service")
    command_runner = mocker.MagicMock(spec=CommandRunner)
    failures = {
        "bus": RunResult(returncode=1, stderr="Failed to connect to bus"),
        "executable": FileNotFoundError("systemctl missing"),
        "timeout": subprocess.TimeoutExpired("systemctl", 30),
    }

    success = RunResult(returncode=0)
    command_runner.run.side_effect = [failures[failure], success, success]
    mocker.patch(
        "virgo_agentic_dag.infra.scheduling.systemd_retirement.SubprocessCommandRunner",
        return_value=command_runner,
    )

    with pytest.raises(SchedulingError, match="systemctl --user disable.*fails"):
        retire_service(service_path)

    assert service_path.read_text() == "service"

    retire_service(service_path)

    assert not service_path.exists()

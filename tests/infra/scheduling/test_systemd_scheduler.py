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
from virgo_agentic_dag.infra.scheduling.systemd_scheduler import SystemdScheduler

pytestmark = pytest.mark.unit

MISSING = RunResult(returncode=1, stdout="LoadState=not-found\nActiveState=inactive\n")
PRESENT = RunResult(returncode=0, stdout="LoadState=loaded\nActiveState=active\n")
NOT_FOUND = RunResult(returncode=4, stdout="not-found\n")
ENABLED = RunResult(returncode=0, stdout="enabled\n")
DISABLED = RunResult(returncode=1, stdout="disabled\n")
LINKED = RunResult(returncode=1, stdout="linked\n")
SUCCESS = RunResult(returncode=0)
UNIT_NAME = "fyi.virgo.dag.demo"


@pytest.fixture
def get_job(tmp_path: Path) -> Callable[..., ScheduledJob]:
    environment = {"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "config")}
    job_values = {
        "dag_name": "demo",
        "label": UNIT_NAME,
        "argv": '["/venv/bin/dagctl", "start"]',
        "interval_seconds": 300,
        "working_directory": str(tmp_path / "run"),
        "log_path": str(tmp_path / "run" / "logs" / "start.log"),
        "environment": json.dumps(environment),
        "created_at": datetime(2026, 8, 2, tzinfo=UTC),
    }

    return lambda **changes: ScheduledJob(**(job_values | changes))


async def test_registration_installs_escaped_units_before_enabling_only_the_timer(
    mocker: MockerFixture, get_job: Callable[..., ScheduledJob], tmp_path: Path
) -> None:
    unit_name = r"fyi.virgo.dag.a\x20\x22\x27\x5c\x24\x25\x2d-\xc3\xa9"
    arguments = ["/venv a\"'\\$%/dagctl", "start", "--dag", "/run a\"'\\$%/dag.toml"]
    argv = json.dumps(arguments)
    working_directory = str(tmp_path / "run a\"'\\$%")
    environment = {
        "HOME": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path / "config custom"),
        "PATH": "/bin a\"'\\$%",
    }
    environment_json = json.dumps(environment)
    job = get_job(
        label="fyi.virgo.dag.a \"'\\$%-/é",
        argv=argv,
        interval_seconds=7,
        working_directory=working_directory,
        log_path=working_directory + "/logs/start.log",
        environment=environment_json,
    )

    unit_directory = tmp_path / "config custom" / "systemd" / "user"
    service_path = unit_directory / f"{unit_name}.service"
    timer_path = unit_directory / f"{unit_name}.timer"
    expected_command = 'ExecStart=:"/venv a\\"\'\\\\$%%/dagctl" "start" "--dag" "/run a\\"\'\\\\$%%/dag.toml"\n'
    expected_timer = "[Timer]\nOnActiveSec=7s\nOnUnitActiveSec=7s\nAccuracySec=1s\n\n[Install]\nWantedBy=timers.target\n"
    enable_operations = ["link", "daemon-reload", "enable"]

    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = ([MISSING, NOT_FOUND] * 2 + [SUCCESS] * 3) * 2

    scheduler = SystemdScheduler(command_runner=command_runner)

    await scheduler.register(job)
    await scheduler.register(job)

    service = service_path.read_text()
    timer = timer_path.read_text()
    assert expected_command in service
    assert f"WorkingDirectory={tmp_path}/run a\"'\\$%%\n" in service
    for stream in ("StandardOutput", "StandardError"):
        assert f"{stream}=append:{tmp_path}/run a\"'\\$%%/logs/start.log\n" in service

    assert '"PATH=/bin a\\"\'\\\\$%%"' in service
    assert "Type=oneshot\n" in service and "KillMode=process\n" in service
    assert "SuccessExitStatus=3 75\n" in service
    assert "StartLimitIntervalSec=0\n" in service
    assert "Restart=" not in service and "RemainAfterExit=" not in service

    assert timer == expected_timer

    unit_paths = list(unit_directory.iterdir())
    assert len(unit_paths) == 2

    log_path = job.get_log_path()
    assert log_path.parent.is_dir()

    commands = [invocation.args[0] for invocation in command_runner.run.call_args_list]
    assert all(command[:2] == ["systemctl", "--user"] for command in commands)
    operations = [command[2] for command in commands]
    assert operations[:7] == ["show", "is-enabled"] * 2 + enable_operations
    assert commands[4][3:] == ["--no-reload", "--", str(service_path), str(timer_path)]
    assert commands[-1][3:] == ["--now", "--", f"{unit_name}.timer"]


@pytest.mark.parametrize(
    ("load_state", "active_state", "file_result", "service_file_result", "expected"),
    [
        ("loaded", "active", ENABLED, ENABLED, True),
        ("not-found", "inactive", NOT_FOUND, ENABLED, False),
        ("loaded", "active", DISABLED, ENABLED, False),
        ("loaded", "inactive", ENABLED, ENABLED, False),
        ("loaded", "active", ENABLED, NOT_FOUND, False),
    ],
)
async def test_registration_lookup_uses_timer_and_service_state(
    load_state: str,
    active_state: str,
    file_result: RunResult,
    service_file_result: RunResult,
    expected: bool,
    mocker: MockerFixture,
    get_job: Callable[..., ScheduledJob],
) -> None:
    job = get_job()

    command_runner = mocker.MagicMock(spec=CommandRunner)
    timer_properties = f"LoadState={load_state}\nActiveState={active_state}"
    timer_result = RunResult(returncode=0, stdout=timer_properties)
    service_properties = "LoadState=loaded\nActiveState=failed"
    service_result = RunResult(returncode=0, stdout=service_properties)
    states = [timer_result, file_result, service_result, service_file_result]
    command_runner.run.side_effect = states

    scheduler = SystemdScheduler(command_runner=command_runner)

    is_registered = await scheduler.is_registered(job)

    assert is_registered is expected


@pytest.mark.parametrize("failure", ["manager", "executable", "timeout"])
async def test_unavailable_systemd_raises_a_scheduling_error(
    failure: str, mocker: MockerFixture, get_job: Callable[..., ScheduledJob]
) -> None:
    job = get_job()

    command_runner = mocker.MagicMock(spec=CommandRunner)
    if failure == "manager":
        failure_result = RunResult(returncode=1, stderr="Failed to connect to bus")
        command_runner.run.return_value = failure_result
    elif failure == "executable":
        command_runner.run.side_effect = FileNotFoundError("systemctl missing")
    else:
        command_runner.run.side_effect = subprocess.TimeoutExpired("systemctl", 30)

    scheduler = SystemdScheduler(command_runner=command_runner)

    with pytest.raises(SchedulingError, match="systemctl --user show.*fails"):
        await scheduler.is_registered(job)


async def test_retirement_removes_units_without_waiting_for_the_current_service(
    mocker: MockerFixture, get_job: Callable[..., ScheduledJob], tmp_path: Path
) -> None:
    job = get_job()
    unit_directory = tmp_path / "config" / "systemd" / "user"
    unit_directory.mkdir(parents=True)
    service_path = unit_directory / f"{UNIT_NAME}.service"
    timer_path = unit_directory / f"{UNIT_NAME}.timer"
    service_path.write_text("service")
    timer_path.write_text("timer")

    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = (
        [PRESENT, LINKED, PRESENT, ENABLED]
        + [SUCCESS] * 3
        + [PRESENT, NOT_FOUND, MISSING, NOT_FOUND, SUCCESS]
    )

    scheduler = SystemdScheduler(command_runner=command_runner)

    await scheduler.retire(job)
    await scheduler.retire(job)

    commands = [call.args[0][2:] for call in command_runner.run.call_args_list]
    assert [command for command in commands if command[0] == "stop"] == [
        ["stop", "--no-block", "--", f"{UNIT_NAME}.timer"]
    ]
    assert [command for command in commands if command[0] == "disable"] == [
        ["disable", "--no-reload", "--", f"{UNIT_NAME}.service", f"{UNIT_NAME}.timer"]
    ]

    unit_paths = list(unit_directory.iterdir())
    assert unit_paths == []


@pytest.mark.parametrize("was_registered", [False, True])
@pytest.mark.parametrize("failed_command", ["reload", "enable", "write", "mkdir"])
async def test_failed_registration_restores_previous_unit_files(
    was_registered: bool,
    failed_command: str,
    mocker: MockerFixture,
    get_job: Callable[..., ScheduledJob],
    tmp_path: Path,
) -> None:
    job = get_job()
    unit_directory = tmp_path / "config" / "systemd" / "user"
    unit_directory.mkdir(parents=True)
    service_path = unit_directory / f"{UNIT_NAME}.service"
    timer_path = unit_directory / f"{UNIT_NAME}.timer"
    if was_registered:
        service_path.write_bytes(b"previous service")
        timer_path.write_bytes(b"previous timer")

    command_runner = mocker.MagicMock(spec=CommandRunner)
    failure_result = RunResult(returncode=1, stderr="activation failed")
    initial_state = [PRESENT, ENABLED] if was_registered else [MISSING, NOT_FOUND]
    activation = [SUCCESS] * (1 if failed_command == "reload" else 2) + [failure_result]
    if failed_command == "write":
        mocker.patch.object(
            Path, "replace", side_effect=PermissionError("activation failed")
        )
        activation = []
    elif failed_command == "mkdir":
        log_path = job.get_log_path()
        log_path.parent.parent.mkdir(parents=True)
        log_path.parent.write_text("file")
        activation = []

    cleanup_file_state = LINKED if activation else NOT_FOUND
    cleanup_count = 3 if activation else 2
    cleanup = (
        [SUCCESS, SUCCESS]
        if was_registered
        else [MISSING, cleanup_file_state] * 2 + [SUCCESS] * cleanup_count
    )
    command_runner.run.side_effect = initial_state * 2 + activation + cleanup

    scheduler = SystemdScheduler(command_runner=command_runner)

    with pytest.raises(SchedulingError, match="activation failed|File exists"):
        await scheduler.register(job)

    if was_registered:
        assert service_path.read_bytes() == b"previous service"
        assert timer_path.read_bytes() == b"previous timer"
        assert all(
            invocation.args[0][2] not in {"stop", "disable"}
            for invocation in command_runner.run.call_args_list
        )
    else:
        unit_paths = list(unit_directory.iterdir())
        assert unit_paths == []
        operations = [call.args[0][2] for call in command_runner.run.call_args_list]
        assert ("disable" in operations) == bool(activation)

import json
import plistlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.infra.scheduling.launchd_scheduler import LaunchdScheduler

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 2, tzinfo=UTC)
USER_ID = 501
LABEL = ScheduledJob.get_label("demo")


@pytest.fixture
def job(tmp_path: Path) -> ScheduledJob:
    return ScheduledJob(
        dag_name="demo",
        label=LABEL,
        argv=json.dumps(["/venv/bin/dagctl", "start", "--dag", "dag.toml"]),
        interval_seconds=300,
        working_directory=str(tmp_path),
        log_path=str(tmp_path / "start.log"),
        environment=json.dumps({"PATH": "/usr/bin"}),
        created_at=NOW,
    )


def read_plist(agents_directory: Path) -> dict[str, object]:
    with (agents_directory / f"{LABEL}.plist").open("rb") as file:
        return dict(plistlib.load(file))


async def test_bootstraps_into_this_users_domain_when_registering(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )

    await scheduler.register(job)

    command_runner.run.assert_called_once_with(
        ("launchctl", "bootstrap", f"gui/{USER_ID}", str(tmp_path / f"{LABEL}.plist"))
    )


async def test_asks_the_host_to_wait_between_runs_when_the_schedule_is_an_interval(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )
    job = ScheduledJob(
        dag_name="demo",
        label=LABEL,
        argv=json.dumps(["/venv/bin/dagctl", "start"]),
        interval_seconds=300,
        working_directory=str(tmp_path),
        log_path=str(tmp_path / "start.log"),
        environment="{}",
        created_at=NOW,
    )

    await scheduler.register(job)

    plist = read_plist(tmp_path)
    assert plist["StartInterval"] == 300
    assert plist["RunAtLoad"] is False


async def test_carries_the_command_and_its_environment_when_writing_the_plist(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )
    job = ScheduledJob(
        dag_name="demo",
        label=LABEL,
        argv=json.dumps(["/venv/bin/dagctl", "start", "--dag", "dag.toml"]),
        interval_seconds=300,
        working_directory=str(tmp_path),
        log_path=str(tmp_path / "start.log"),
        environment=json.dumps({"PATH": "/usr/bin"}),
        created_at=NOW,
    )

    await scheduler.register(job)

    plist = read_plist(tmp_path)
    assert plist["Label"] == LABEL
    assert plist["ProgramArguments"] == [
        "/venv/bin/dagctl",
        "start",
        "--dag",
        "dag.toml",
    ]
    assert plist["EnvironmentVariables"] == {"PATH": "/usr/bin"}
    assert plist["StandardOutPath"] == str(tmp_path / "start.log")


async def test_raises_when_launchd_refuses_to_register(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=1, stderr="launchd said no")

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )

    with pytest.raises(SchedulingError, match="launchd said no"):
        await scheduler.register(job)


async def test_boots_it_out_and_deletes_the_plist_when_retiring(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0)

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )
    await scheduler.register(job)

    await scheduler.retire(job)

    assert command_runner.run.call_args_list[1] == call(
        ("launchctl", "bootout", f"gui/{USER_ID}/{LABEL}")
    )
    assert not (tmp_path / f"{LABEL}.plist").exists()


async def test_stays_quiet_when_retiring_a_job_the_host_no_longer_holds(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [
        RunResult(returncode=1, stderr="launchd said no"),
        RunResult(returncode=1),
    ]

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )

    await scheduler.retire(job)

    assert not (tmp_path / f"{LABEL}.plist").exists()


async def test_raises_when_the_host_still_holds_a_job_it_refused_to_retire(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [
        RunResult(returncode=1, stderr="launchd said no"),
        RunResult(returncode=0),
    ]

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )

    with pytest.raises(SchedulingError, match="launchd said no"):
        await scheduler.retire(job)


@pytest.mark.parametrize(
    ("returncode", "expected"), [(0, True), (1, False)], ids=["loaded", "unknown"]
)
async def test_reports_what_the_host_already_holds_under_this_label(
    returncode: int,
    expected: bool,
    mocker: MockerFixture,
    job: ScheduledJob,
    tmp_path: Path,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=returncode)

    scheduler = LaunchdScheduler(
        command_runner=command_runner, agents_directory=tmp_path, user_id=USER_ID
    )

    registered = await scheduler.is_registered(job)

    assert registered is expected
    command_runner.run.assert_called_once_with(("launchctl", "list", LABEL))


async def test_retire_deletes_the_plist_before_asking_launchd(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    agents_directory = tmp_path / "agents"
    agents_directory.mkdir()
    plist_path = agents_directory / f"{LABEL}.plist"
    plist_path.write_bytes(b"stub")
    present_at_bootout: list[bool] = []

    def watch_plist(_: tuple[str, ...]) -> RunResult:
        """Record whether the plist still existed when launchd was asked to bootout."""
        present_at_bootout.append(plist_path.exists())

        return RunResult(returncode=0)

    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = watch_plist

    scheduler = LaunchdScheduler(
        command_runner=command_runner,
        agents_directory=agents_directory,
        user_id=USER_ID,
    )

    await scheduler.retire(job)

    assert present_at_bootout == [False]
    assert not plist_path.exists()

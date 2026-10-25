import os
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.utils.process import is_process_alive

pytestmark = pytest.mark.integration


@pytest.fixture
def process() -> Iterator[subprocess.Popen[bytes]]:
    running_process = subprocess.Popen(["sleep", "30"])
    try:
        yield running_process
    finally:
        running_process.terminate()
        running_process.wait(timeout=5)


async def test_is_process_alive_returns_true_when_a_live_pid_has_a_matching_start_time(
    process: subprocess.Popen[bytes],
) -> None:
    started_at = datetime.now(UTC)

    is_alive = await is_process_alive(process.pid, started_at)

    assert is_alive is True


async def test_is_process_alive_returns_false_when_a_live_pid_has_a_different_start_time(
    process: subprocess.Popen[bytes],
) -> None:
    started_at = datetime.now(UTC) - timedelta(days=1)

    is_alive = await is_process_alive(process.pid, started_at)

    assert is_alive is False


async def test_is_process_alive_returns_false_when_the_pid_has_exited(
    process: subprocess.Popen[bytes],
) -> None:
    started_at = datetime.now(UTC)
    process.terminate()
    process.wait(timeout=5)

    is_alive = await is_process_alive(process.pid, started_at)

    assert is_alive is False


async def test_is_process_alive_returns_false_when_signal_permission_is_denied(
    mocker: MockerFixture,
) -> None:
    mocker.patch("os.kill", side_effect=PermissionError)
    pid = os.getpid()
    started_at = datetime.now(UTC)

    is_alive = await is_process_alive(pid, started_at)

    assert is_alive is False


@pytest.mark.parametrize(
    ("difference_seconds", "expected_is_alive"), [(3, True), (4, False)]
)
async def test_is_process_alive_requires_a_start_time_within_the_tolerance(
    mocker: MockerFixture, difference_seconds: int, expected_is_alive: bool
) -> None:
    process_status = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=b"Sun Oct 25 10:00:00 2026\n"
    )

    mocker.patch("anyio.run_process", return_value=process_status)

    started_at = datetime(2026, 10, 25, 10, tzinfo=UTC)
    recorded_started_at = started_at + timedelta(seconds=difference_seconds)
    recorded_started_at_without_timezone = recorded_started_at.replace(tzinfo=None)
    pid = os.getpid()

    is_alive = await is_process_alive(pid, recorded_started_at_without_timezone)

    assert is_alive is expected_is_alive

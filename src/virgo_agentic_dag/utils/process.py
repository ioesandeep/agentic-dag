"""The liveness check for a process the framework started."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime

import anyio

from virgo_agentic_dag.config.constants import PROCESS_START_TOLERANCE_SECONDS


async def get_process_started_at(pid: int) -> datetime | None:
    """Return the operating system's start time for an existing process."""
    if pid <= 0:
        return None

    pid_text = str(pid)
    try:
        with anyio.fail_after(5):
            process_status = await anyio.run_process(
                ["ps", "-o", "lstart=", "-p", pid_text],
                env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
                check=True,
            )

        process_output = process_status.stdout.decode("ascii")
        process_start_text = process_output.strip()
        started_at = datetime.strptime(process_start_text, "%a %b %d %H:%M:%S %Y")

        return started_at.replace(tzinfo=UTC)
    except (PermissionError, subprocess.SubprocessError, TimeoutError, ValueError):
        return None


async def is_process_alive(pid: int, started_at: datetime) -> bool:
    """Report whether the recorded process is still running."""
    if pid <= 0:
        return False

    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    except PermissionError:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return False

    process_started_at = await get_process_started_at(pid)
    if process_started_at is None:
        return False

    recorded_started_at = (
        started_at.replace(tzinfo=UTC) if started_at.tzinfo is None else started_at
    )

    start_difference = process_started_at - recorded_started_at
    difference_seconds = start_difference.total_seconds()

    return abs(difference_seconds) <= PROCESS_START_TOLERANCE_SECONDS

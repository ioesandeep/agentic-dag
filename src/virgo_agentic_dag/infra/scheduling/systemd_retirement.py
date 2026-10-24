import asyncio
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.infra.host.subprocess_command_runner import (
    SubprocessCommandRunner,
)
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.labels.en import LABELS


@asynccontextmanager
async def lock_units(service_path: Path) -> AsyncIterator[None]:
    """Serializes registration and removal of one job's unit files."""
    unit_lock = get_unit_lock(service_path)
    try:
        await _acquire_lock(unit_lock)
    except OSError as error:
        message = LABELS["systemdFileFailed"].format(job=service_path.name, error=error)

        raise SchedulingError(message) from error

    try:
        yield
    finally:
        unit_lock.release()


def get_unit_lock(service_path: Path) -> DagRunLock:
    """Creates a lock with a bounded filename for one scheduled service."""
    identity = service_path.name.encode()
    identity_hash = sha256(identity)
    digest = identity_hash.hexdigest()
    lock_path = service_path.parent / ("retire-" + digest)

    return DagRunLock(lock_path)


async def _acquire_lock(unit_lock: DagRunLock) -> None:
    while True:
        invocation = asyncio.to_thread(unit_lock.acquire)
        acquisition = asyncio.create_task(invocation)
        try:
            await asyncio.shield(acquisition)

            return
        except RunBusy:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            try:
                await acquisition
            except RunBusy:
                pass
            finally:
                unit_lock.release()

            raise


def get_retirement_command(service_path: Path) -> list[str]:
    """Orders service cleanup after the current systemd invocation."""
    service_path_text = str(service_path)
    service_argument = service_path_text.replace("$", "$$")

    python_executable = sys.executable.replace("$", "$$")
    service_name = service_path.name.replace("\\", "\\\\")

    return [
        "--collect",
        "--no-block",
        "--property=After=" + service_name,
        python_executable,
        "-m",
        "virgo_agentic_dag.infra.scheduling.systemd_retirement",
        service_argument,
    ]


def retire_service(service_path: Path) -> None:
    """Removes a retired service after systemd completes its invocation."""
    unit_lock = get_unit_lock(service_path)
    unit_lock.acquire_waiting()
    try:
        timer_path = service_path.with_suffix(".timer")
        timer_exists = timer_path.exists()
        service_exists = service_path.exists()
        if timer_exists or not service_exists:
            return

        _run_systemctl(["disable", "--no-reload", "--", service_path.name])
        service_path.unlink(missing_ok=True)
        _run_systemctl(["daemon-reload"])
    finally:
        unit_lock.release()


def _run_systemctl(arguments: list[str]) -> None:
    command_runner = SubprocessCommandRunner(timeout_seconds=30)
    command = ["systemctl", "--user", *arguments]
    command_text = " ".join(command)
    try:
        run_result = command_runner.run(command)
    except (OSError, subprocess.TimeoutExpired) as error:
        message = LABELS["systemdCommandFailed"].format(
            command=command_text, error=error
        )

        raise SchedulingError(message) from error

    if run_result.returncode != 0:
        message = LABELS["systemdCommandFailed"].format(
            command=command_text, error=run_result.stderr
        )

        raise SchedulingError(message)


if __name__ == "__main__":
    service_path = Path(sys.argv[1])
    retire_service(service_path)

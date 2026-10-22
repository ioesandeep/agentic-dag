import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from anyio import Path as AsyncPath
from pytest_mock import MockerFixture

from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.learning.extraction_lock_state_enum import (
    ExtractionLockStateEnum,
)

pytestmark = pytest.mark.behavior


@pytest.fixture
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "learning_extraction.lock"


@pytest.fixture
def dead_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()

    return process.pid


@pytest.fixture
def session_pid() -> int:
    return 4242


async def test_get_state_returns_free_when_the_lock_file_is_missing(
    lock_path: Path,
) -> None:
    lock = ExtractionLock(lock_path)

    state = await lock.get_state()

    assert state is ExtractionLockStateEnum.FREE


@pytest.mark.parametrize("node_ids", [[], ["A", "B"]])
async def test_get_state_returns_held_when_the_process_of_the_lock_file_is_running(
    lock_path: Path, node_ids: list[str]
) -> None:
    pid = os.getpid()

    lock_file_lines = [str(pid), *node_ids]
    lock_file_content = "\n".join(lock_file_lines)
    lock_path.write_text(lock_file_content, encoding="utf-8")

    lock = ExtractionLock(lock_path)

    state = await lock.get_state()

    assert state is ExtractionLockStateEnum.HELD


async def test_get_state_returns_unreadable_when_the_lock_file_is_empty(
    lock_path: Path,
) -> None:
    lock_path.write_text("", encoding="utf-8")
    lock = ExtractionLock(lock_path)

    state = await lock.get_state()

    assert state is ExtractionLockStateEnum.UNREADABLE


async def test_is_free_returns_false_when_the_lock_file_contains_no_process_id(
    lock_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    lock_path.write_text("", encoding="utf-8")
    lock = ExtractionLock(lock_path)

    is_free = await lock.is_free()

    assert is_free is False

    logged_levels = [record.levelname for record in caplog.records]

    assert logged_levels == ["WARNING"]


async def test_acquire_writes_the_process_id_of_the_caller_when_the_previous_process_has_exited(
    lock_path: Path, dead_pid: int
) -> None:
    lock_path.write_text(str(dead_pid), encoding="utf-8")
    pid = os.getpid()
    lock = ExtractionLock(lock_path)

    is_acquired = await lock.acquire()

    assert is_acquired is True
    assert lock_path.read_text(encoding="utf-8") == str(pid)


async def test_acquire_returns_false_when_the_lock_is_held(lock_path: Path) -> None:
    first_lock = ExtractionLock(lock_path)
    is_acquired = await first_lock.acquire()

    assert is_acquired is True

    second_lock = ExtractionLock(lock_path)

    is_acquired_again = await second_lock.acquire()

    assert is_acquired_again is False


@pytest.mark.parametrize("cancellation_count", [1, 2])
async def test_acquire_records_the_pid_before_propagating_task_cancellation(
    mocker: MockerFixture, lock_path: Path, cancellation_count: int
) -> None:
    """The PID write waits so cancellation occurs after exclusive file creation."""
    write_started = asyncio.Event()
    finish_write = asyncio.Event()
    original_write_text = AsyncPath.write_text

    async def write_after_cancellation(
        async_path: AsyncPath, content: str, encoding: str
    ) -> int:
        write_started.set()
        await finish_write.wait()

        return await original_write_text(async_path, content, encoding=encoding)

    mocker.patch.object(
        AsyncPath, "write_text", autospec=True, side_effect=write_after_cancellation
    )

    lock = ExtractionLock(lock_path)
    lock_acquisition = lock.acquire()
    lock_acquisition_task = asyncio.create_task(lock_acquisition)
    await write_started.wait()

    for _ in range(cancellation_count):
        lock_acquisition_task.cancel("stop acquisition")
        await asyncio.sleep(0)

    is_acquisition_pending = not lock_acquisition_task.done()
    finish_write.set()

    with pytest.raises(asyncio.CancelledError, match="stop acquisition"):
        await lock_acquisition_task

    assert is_acquisition_pending is True
    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


async def test_record_session_pid_preserves_the_node_ids_for_the_learning_session(
    lock_path: Path, session_pid: int
) -> None:
    lock = ExtractionLock(lock_path)
    await lock.acquire()

    await lock.record_session_pid(session_pid, ["A", "B"])

    assert lock_path.read_text(encoding="utf-8") == f"{session_pid}\nA\nB"
    assert await lock.get_session_pid() == session_pid
    assert await lock.get_session_node_ids() == ["A", "B"]

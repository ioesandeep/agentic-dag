import os
import subprocess
from pathlib import Path

import pytest
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


def test_get_state_returns_free_when_the_lock_file_is_missing(lock_path: Path) -> None:
    lock = ExtractionLock(lock_path)

    state = lock.get_state()

    assert state is ExtractionLockStateEnum.FREE


def test_get_state_returns_held_when_the_process_of_the_lock_file_is_running(
    lock_path: Path,
) -> None:
    pid = os.getpid()
    lock_path.write_text(str(pid), encoding="utf-8")
    lock = ExtractionLock(lock_path)

    state = lock.get_state()

    assert state is ExtractionLockStateEnum.HELD


def test_get_state_returns_unreadable_when_the_lock_file_is_empty(
    lock_path: Path,
) -> None:
    lock_path.write_text("", encoding="utf-8")
    lock = ExtractionLock(lock_path)

    state = lock.get_state()

    assert state is ExtractionLockStateEnum.UNREADABLE


def test_is_free_returns_false_when_the_lock_file_contains_no_process_id(
    lock_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    lock_path.write_text("", encoding="utf-8")
    lock = ExtractionLock(lock_path)

    is_free = lock.is_free()

    assert is_free is False
    logged_levels = [record.levelname for record in caplog.records]
    assert logged_levels == ["WARNING"]


def test_acquire_writes_the_process_id_of_the_caller_when_the_previous_process_has_exited(
    lock_path: Path, dead_pid: int
) -> None:
    lock_path.write_text(str(dead_pid), encoding="utf-8")
    pid = os.getpid()
    lock = ExtractionLock(lock_path)

    is_acquired = lock.acquire()

    assert is_acquired is True
    assert lock_path.read_text(encoding="utf-8") == str(pid)


def test_acquire_returns_false_when_the_lock_is_held(lock_path: Path) -> None:
    first_lock = ExtractionLock(lock_path)
    is_acquired = first_lock.acquire()
    assert is_acquired is True
    second_lock = ExtractionLock(lock_path)

    is_acquired_again = second_lock.acquire()

    assert is_acquired_again is False


def test_record_session_pid_replaces_the_contents_with_the_process_id_of_the_session(
    lock_path: Path, session_pid: int
) -> None:
    lock = ExtractionLock(lock_path)
    lock.acquire()

    lock.record_session_pid(session_pid)

    assert lock_path.read_text(encoding="utf-8") == str(session_pid)

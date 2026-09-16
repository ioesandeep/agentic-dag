"""The lock file that serializes learning extraction sessions over one run."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from virgo_agentic_dag.services.learning.extraction_lock_state_enum import (
    ExtractionLockStateEnum,
)
from virgo_agentic_dag.utils.process import is_process_alive

logger = logging.getLogger(__name__)


class ExtractionLock:
    """Prevents a second learning extraction session from starting while one is running."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path

    def get_state(self) -> ExtractionLockStateEnum:
        """Return whether the lock is free, held by a running process, or unreadable."""
        try:
            lock_file_content = self._lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ExtractionLockStateEnum.FREE

        try:
            pid = int(lock_file_content.strip())
        except ValueError:
            return ExtractionLockStateEnum.UNREADABLE

        is_lock_process_alive = is_process_alive(pid)
        if is_lock_process_alive:
            return ExtractionLockStateEnum.HELD

        return ExtractionLockStateEnum.FREE

    def is_free(self) -> bool:
        """Report whether this lock may be taken."""
        state = self.get_state()
        if state is ExtractionLockStateEnum.UNREADABLE:
            logger.warning(
                "the learning extraction lock file does not contain a process id. "
                "Delete the file by hand."
            )

            return False

        return state is ExtractionLockStateEnum.FREE

    def acquire(self) -> bool:
        """Take the lock for the calling process when the lock is free."""
        state = self.get_state()
        if state is ExtractionLockStateEnum.FREE:
            self._lock_path.unlink(missing_ok=True)

        try:
            descriptor = os.open(
                self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
        except FileExistsError:
            return False

        pid = os.getpid()
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(pid))

        return True

    def record_session_pid(self, pid: int) -> None:
        """Record the process id of the launched session, replacing the one before it."""
        self._lock_path.write_text(str(pid), encoding="utf-8")

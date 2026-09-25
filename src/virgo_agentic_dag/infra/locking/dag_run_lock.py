"""The advisory file lock that serializes passes over one dag."""

from __future__ import annotations

import fcntl
import time
from contextlib import suppress
from pathlib import Path
from typing import TextIO

from virgo_agentic_dag.config.constants import RUN_LOCK_RETRY_INTERVAL_SECONDS
from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.locking.run_lock_config import RunLockConfig


class DagRunLock(RunLock):
    """Holds a dag's run through a lock the kernel releases with the process, so a
    dead pass never leaves the run held."""

    def __init__(self, db_path: Path) -> None:
        self._lock_path = db_path.parent / f"{db_path.name}.lock"
        self._file: TextIO | None = None

    def acquire(self) -> None:
        """Claim the run, refusing with RunBusy when another pass already holds it."""
        file = self._open_lock_file()

        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            file.close()

            raise RunBusy(
                f"another pass is already working the run at {self._lock_path.parent}"
            ) from error

        self._file = file

    def acquire_waiting(self) -> None:
        """Claim the run once its holder finishes, waiting as long as that takes."""
        file = self._open_lock_file()
        fcntl.flock(file, fcntl.LOCK_EX)

        self._file = file

    def acquire_lock(self, run_lock_config: RunLockConfig) -> None:
        """Claim the run, waiting without limit when the config's timeout is None and
        raising RunBusy when the run lock remains unavailable through the timeout."""
        if run_lock_config.timeout is None:
            self.acquire_waiting()
        else:
            self._acquire_within(run_lock_config.timeout)

    def release(self) -> None:
        """Give the run back, so the next pass can claim it."""
        if self._file is None:
            return

        fcntl.flock(self._file, fcntl.LOCK_UN)
        self._file.close()
        self._file = None

    def _acquire_within(self, timeout: float) -> None:
        """Claim the run or raise RunBusy when the run lock remains unavailable through the timeout."""
        deadline = time.monotonic() + timeout
        remaining_seconds = timeout
        while remaining_seconds > 0:
            with suppress(RunBusy):
                self.acquire()

                return

            time.sleep(RUN_LOCK_RETRY_INTERVAL_SECONDS)
            remaining_seconds = deadline - time.monotonic()

        self.acquire()

    def _open_lock_file(self) -> TextIO:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        return self._lock_path.open("w")

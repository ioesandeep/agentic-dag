"""The advisory file lock that serializes passes over one dag."""

from __future__ import annotations

import fcntl
from pathlib import Path
from typing import TextIO

from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock


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

    def release(self) -> None:
        """Give the run back, so the next pass can claim it."""
        if self._file is None:
            return

        fcntl.flock(self._file, fcntl.LOCK_UN)
        self._file.close()
        self._file = None

    def _open_lock_file(self) -> TextIO:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        return self._lock_path.open("w")

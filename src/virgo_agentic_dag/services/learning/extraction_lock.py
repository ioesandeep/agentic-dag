"""The lock file that serializes learning extraction sessions over one run."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from anyio import CancelScope
from anyio import Path as AsyncPath
from anyio.lowlevel import checkpoint_if_cancelled

from virgo_agentic_dag.services.learning.extraction_lock_state_enum import (
    ExtractionLockStateEnum,
)
from virgo_agentic_dag.utils.process import get_process_started_at, is_process_alive

logger = logging.getLogger(__name__)


class ExtractionLock:
    """Prevents a second learning extraction session from starting while one is running."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = AsyncPath(lock_path)

    async def get_state(self) -> ExtractionLockStateEnum:
        """Return whether the lock is free, held by a running process, or unreadable."""
        try:
            lock_file_content = await self._lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ExtractionLockStateEnum.FREE

        try:
            pid = await self._get_live_pid_from_content(lock_file_content)
        except ValueError:
            return ExtractionLockStateEnum.UNREADABLE

        if pid is not None:
            return ExtractionLockStateEnum.HELD

        return ExtractionLockStateEnum.FREE

    async def _get_live_pid_from_content(self, lock_file_content: str) -> int | None:
        pid_text = lock_file_content.partition("\n")[0]
        pid = int(pid_text)
        started_at = await self._get_recorded_started_at(lock_file_content)
        if started_at is None:
            return None

        is_lock_process_alive = await is_process_alive(pid, started_at)

        if is_lock_process_alive:
            return pid

        return None

    async def _get_recorded_started_at(self, lock_file_content: str) -> datetime | None:
        lock_file_lines = lock_file_content.splitlines()
        has_recorded_start = len(lock_file_lines) > 1 and lock_file_lines[1].startswith(
            "started_at="
        )

        if has_recorded_start:
            started_at_text = lock_file_lines[1].removeprefix("started_at=")

            return datetime.fromisoformat(started_at_text)

        return await self.get_written_at()

    async def is_free(self) -> bool:
        """Report whether this lock may be taken."""
        state = await self.get_state()
        if state is ExtractionLockStateEnum.UNREADABLE:
            logger.warning(
                "the learning extraction lock file does not contain a process id. "
                "Delete the file by hand."
            )

            return False

        return state is ExtractionLockStateEnum.FREE

    async def acquire(self) -> bool:
        """Take the lock for the calling process when the lock is free."""
        state = await self.get_state()
        if state is ExtractionLockStateEnum.FREE:
            await self._lock_path.unlink(missing_ok=True)

        lock_creation = self._create_lock()
        lock_creation_task = asyncio.create_task(lock_creation)
        cancellation_error: asyncio.CancelledError | None = None

        with CancelScope(shield=True):
            is_lock_creation_done = lock_creation_task.done()
            while not is_lock_creation_done:
                try:
                    await asyncio.shield(lock_creation_task)
                except asyncio.CancelledError as error:
                    cancellation_error = error

                is_lock_creation_done = lock_creation_task.done()

        is_acquired = lock_creation_task.result()
        if cancellation_error is not None:
            raise cancellation_error

        await checkpoint_if_cancelled()

        return is_acquired

    async def _create_lock(self) -> bool:
        try:
            await self._lock_path.touch(mode=0o644, exist_ok=False)
        except FileExistsError:
            return False

        pid = os.getpid()
        await self.record_session_pid(pid)

        return True

    async def record_session_pid(
        self, pid: int, node_ids: list[str] | None = None
    ) -> None:
        """Record the learning session's process id and node ids."""
        process_started_at = await get_process_started_at(pid)
        lock_file_lines = [str(pid)]
        if process_started_at is not None:
            started_at_text = process_started_at.isoformat()
            lock_file_lines.append(f"started_at={started_at_text}")

        lock_file_lines.extend(node_ids or [])
        lock_file_content = "\n".join(lock_file_lines)
        await self._lock_path.write_text(lock_file_content, encoding="utf-8")

    async def get_live_session_pid(self) -> int | None:
        """Return the learning session's process id when its identity matches."""
        try:
            lock_file_content = await self._lock_path.read_text(encoding="utf-8")

            return await self._get_live_pid_from_content(lock_file_content)
        except (FileNotFoundError, ValueError):
            return None

    async def get_session_pid(self) -> int | None:
        """Return the learning session's recorded process id."""
        try:
            lock_file_content = await self._lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

        try:
            pid_text = lock_file_content.partition("\n")[0]

            return int(pid_text)
        except ValueError:
            return None

    async def get_session_node_ids(self) -> list[str]:
        """Return the node IDs assigned to the learning session."""
        try:
            lock_file_content = await self._lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []

        lock_file_lines = lock_file_content.splitlines()[1:]
        has_recorded_start = bool(lock_file_lines) and lock_file_lines[0].startswith(
            "started_at="
        )

        if has_recorded_start:
            return lock_file_lines[1:]

        return lock_file_lines

    async def get_written_at(self) -> datetime | None:
        """Return when the extraction lock was last written."""
        try:
            lock_stat = await self._lock_path.stat()
        except FileNotFoundError:
            return None

        return datetime.fromtimestamp(lock_stat.st_mtime, UTC)

    async def release(self) -> None:
        """Allow another learning extraction session to start."""
        await self._lock_path.unlink(missing_ok=True)

"""Keeps the watcher process running between passes and kills it when the run ends."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.dag_utils import get_dag_watch_log_path
from virgo_agentic_dag.utils.format_label import format_label
from virgo_agentic_dag.utils.process import is_process_alive


class WatcherService:
    """Keeps a run's watcher alive until the run ends."""

    def __init__(self, watcher_repo: WatcherRepo, executable: Path) -> None:
        self._watcher_repo = watcher_repo
        self._executable = executable

    async def watch(self, dag_name: str) -> None:
        """Make sure this run's watcher is running."""
        watcher = await self._watcher_repo.get_by_dag_name(dag_name)
        if watcher is not None and is_process_alive(watcher.pid):
            return

        pid = await asyncio.to_thread(self._spawn, dag_name)
        fresh = Watcher(dag_name=dag_name, pid=pid, started_at=datetime.now(UTC))
        await self._watcher_repo.save(fresh)
        emit(format_label(LABELS["watcherStarted"], {"dag": dag_name}) + "\n")

    async def stop(self, dag_name: str) -> None:
        """End this run's watcher."""
        watcher = await self.forget(dag_name)
        if watcher is None:
            return

        self.kill(watcher)

    async def forget(self, dag_name: str) -> Watcher | None:
        """Delete the run's watcher row and return it, leaving the kill to the caller."""
        watcher = await self._watcher_repo.get_by_dag_name(dag_name)
        if watcher is None:
            return None

        await self._watcher_repo.delete(watcher)
        emit(format_label(LABELS["watcherStopped"], {"dag": dag_name}) + "\n")

        return watcher

    def kill(self, watcher: Watcher) -> None:
        """Terminate the watcher's process group, idempotently."""
        try:
            os.killpg(watcher.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return

    def _spawn(self, dag_name: str) -> int:
        log_path = get_dag_watch_log_path(dag_name)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as log:
            process = subprocess.Popen(
                [str(self._executable), "watch", dag_name],
                env=dict(os.environ),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        return process.pid

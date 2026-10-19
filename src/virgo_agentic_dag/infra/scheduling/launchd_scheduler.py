"""Scheduler on macOS through launchd, one user agent plist per job."""

from __future__ import annotations

import asyncio
import plistlib
from pathlib import Path
from typing import Any

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler


class LaunchdScheduler(Scheduler):
    """Writes a plist per job and bootstraps it into this user's launchd domain."""

    def __init__(
        self, command_runner: CommandRunner, agents_directory: Path, user_id: int
    ) -> None:
        self._command_runner = command_runner
        self._agents_directory = agents_directory
        self._user_id = user_id

    async def register(self, job: ScheduledJob) -> None:
        """Register the job with launchd, replacing any job under its label."""
        is_registered = await self.is_registered(job)
        if is_registered:
            await self.retire(job)

        path = await asyncio.to_thread(self._write_plist, job)
        domain = self._get_domain()
        argv = ("launchctl", "bootstrap", domain, str(path))
        try:
            result = await self._run(argv)
        except Exception:
            await asyncio.to_thread(path.unlink, missing_ok=True)

            raise

        if result.returncode != 0:
            await asyncio.to_thread(path.unlink, missing_ok=True)

            raise SchedulingError(
                f"launchd failed to register {job.label}: {result.stderr.strip()}"
            )

    def _write_plist(self, job: ScheduledJob) -> Path:
        path = self._get_plist_path(job.label)
        path.parent.mkdir(parents=True, exist_ok=True)

        log_path = job.get_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        plist = self._build_plist(job)
        with path.open("wb") as file:
            plistlib.dump(plist, file)

        return path

    async def retire(self, job: ScheduledJob) -> None:
        """Unregister this job from launchd, which may terminate the calling process."""
        self._get_plist_path(job.label).unlink(missing_ok=True)

        result = await self._run(
            ("launchctl", "bootout", f"{self._get_domain()}/{job.label}")
        )
        if result.returncode != 0 and await self.is_registered(job):
            raise SchedulingError(
                f"launchd refused to retire {job.label}: {result.stderr.strip()}"
            )

    async def is_registered(self, job: ScheduledJob) -> bool:
        """Report whether launchd already holds this job."""
        result = await self._run(("launchctl", "list", job.label))

        return result.returncode == 0

    async def _run(self, argv: tuple[str, ...]) -> RunResult:
        return await asyncio.to_thread(self._command_runner.run, argv)

    def _get_domain(self) -> str:
        return f"gui/{self._user_id}"

    def _get_plist_path(self, label: str) -> Path:
        return self._agents_directory / f"{label}.plist"

    def _build_plist(self, job: ScheduledJob) -> dict[str, Any]:
        environment = job.get_environment()
        plist: dict[str, Any] = {
            "Label": job.label,
            "ProgramArguments": job.get_argv(),
            "WorkingDirectory": str(job.get_working_directory()),
            "StandardOutPath": str(job.get_log_path()),
            "StandardErrorPath": str(job.get_log_path()),
            "RunAtLoad": False,
            "StartInterval": job.interval_seconds,
        }
        if environment:
            plist["EnvironmentVariables"] = dict(environment)

        return plist

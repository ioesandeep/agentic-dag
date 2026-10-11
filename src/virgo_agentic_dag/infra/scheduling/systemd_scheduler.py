from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.infra.scheduling.systemd_unit import SystemdUnit
from virgo_agentic_dag.labels.en import LABELS


@dataclass(frozen=True)
class SystemdUnitState:
    """Records a scheduled unit's state in systemd."""

    load_state: str
    active_state: str
    unit_file_state: str


class SystemdScheduler(Scheduler):
    """Schedules recurring DAG ticks for the current Unix account."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def register(self, job: ScheduledJob) -> None:
        """Registers a scheduled job with systemd."""
        unit_files = await asyncio.to_thread(SystemdUnit.list_for_job, job)
        was_registered = await self.is_registered(job)
        try:
            previous_files = await asyncio.to_thread(
                self._get_previous_files, unit_files
            )
        except OSError as error:
            message = LABELS["systemdFileFailed"].format(job=job.label, error=error)

            raise SchedulingError(message) from error

        try:
            await asyncio.to_thread(self._install_files, job, unit_files)
            await self._activate(job, unit_files)
        except (OSError, SchedulingError) as error:
            await self._rollback(job, previous_files, was_registered, error)
            message = LABELS["systemdRegisterFailed"].format(job=job.label, error=error)

            raise SchedulingError(message) from error

    async def _activate(self, job: ScheduledJob, unit_files: list[SystemdUnit]) -> None:
        unit_paths = [str(unit.path) for unit in unit_files]
        await self._run(["link", "--no-reload", "--", *unit_paths])
        await self._run(["daemon-reload"])

        timer_name = SystemdUnit.get_name(job) + ".timer"
        await self._run(["enable", "--now", "--", timer_name])

    async def retire(self, job: ScheduledJob) -> None:
        """Removes future ticks while the current invocation completes."""
        unit_files = await asyncio.to_thread(SystemdUnit.list_for_job, job)
        try:
            await self._disable_units(unit_files)

            removed_files = [SystemdUnit(unit.path, None) for unit in unit_files]
            await asyncio.to_thread(self._write_files, removed_files)

            await self._run(["daemon-reload"])
        except OSError as error:
            message = LABELS["systemdFileFailed"].format(job=job.label, error=error)

            raise SchedulingError(message) from error

    async def _disable_units(self, unit_files: list[SystemdUnit]) -> None:
        unit_names: list[str] = []
        for unit in unit_files:
            unit_state = await self._get_unit_state(unit.path.name)
            if unit_state.unit_file_state in {"enabled", "linked"}:
                unit_names.append(unit.path.name)

            if unit.path.suffix == ".timer" and unit_state.active_state == "active":
                await self._run(["stop", "--no-block", "--", unit.path.name])

        if unit_names:
            await self._run(["disable", "--no-reload", "--", *unit_names])

    async def is_registered(self, job: ScheduledJob) -> bool:
        """Checks whether systemd can continue the job's recurring ticks."""
        unit_name = SystemdUnit.get_name(job)
        timer_state = await self._get_unit_state(unit_name + ".timer")
        service_state = await self._get_unit_state(unit_name + ".service")

        return (
            timer_state.load_state == "loaded"
            and timer_state.unit_file_state == "enabled"
            and timer_state.active_state == "active"
            and service_state.load_state == "loaded"
            and service_state.unit_file_state != "not-found"
        )

    async def _get_unit_state(self, unit_name: str) -> SystemdUnitState:
        command = [
            "show",
            "--property=LoadState,ActiveState",
            "--",
            unit_name,
        ]
        run_result = await self._run(command, missing_ok=True)
        properties = run_result.stdout.splitlines()
        assignments = [line.split("=", 1) for line in properties if "=" in line]
        unit_state = dict(assignments)
        if "LoadState" not in unit_state:
            message = LABELS["systemdStateMissing"].format(unit=unit_name)

            raise SchedulingError(message)

        load_state = unit_state["LoadState"]
        active_state = unit_state.get("ActiveState", "")

        file_result = await self._run(["is-enabled", "--", unit_name], missing_ok=True)
        unit_file_state = file_result.stdout.strip()

        return SystemdUnitState(load_state, active_state, unit_file_state)

    async def _run(self, arguments: list[str], missing_ok: bool = False) -> RunResult:
        command = ["systemctl", "--user", *arguments]
        command_text = " ".join(command)
        try:
            run_result = await asyncio.to_thread(self._command_runner.run, command)
        except (OSError, subprocess.TimeoutExpired) as error:
            message = LABELS["systemdCommandFailed"].format(
                command=command_text, error=error
            )

            raise SchedulingError(message) from error

        properties = run_result.stdout.splitlines()
        is_missing = missing_ok and "LoadState=not-found" in properties
        is_file_state = self._is_not_enabled(arguments[0], run_result)
        if run_result.returncode != 0 and not is_missing and not is_file_state:
            error_text = run_result.stderr.strip() or str(run_result.returncode)
            message = LABELS["systemdCommandFailed"].format(
                command=command_text, error=error_text
            )

            raise SchedulingError(message)

        return run_result

    @staticmethod
    def _is_not_enabled(command: str, run_result: RunResult) -> bool:
        file_state = run_result.stdout.strip()

        return command == "is-enabled" and (
            run_result.returncode == 1
            and file_state
            in {"disabled", "linked", "linked-runtime", "masked", "masked-runtime"}
            or run_result.returncode == 4
            and file_state == "not-found"
        )

    async def _rollback(
        self,
        job: ScheduledJob,
        previous_files: list[SystemdUnit],
        was_registered: bool,
        registration_error: Exception,
    ) -> None:
        try:
            try:
                if not was_registered:
                    await self.retire(job)
            finally:
                await asyncio.to_thread(self._write_files, previous_files)

            await self._run(["daemon-reload"])
            if was_registered:
                timer_name = SystemdUnit.get_name(job) + ".timer"
                await self._run(["enable", "--now", "--", timer_name])

        except (OSError, SchedulingError) as error:
            message = LABELS["systemdRollbackFailed"].format(
                job=job.label, error=registration_error, cleanup_error=error
            )

            raise SchedulingError(message) from registration_error

    def _get_previous_files(self, unit_files: list[SystemdUnit]) -> list[SystemdUnit]:
        previous_files: list[SystemdUnit] = []
        for unit in unit_files:
            try:
                content = unit.path.read_bytes()
            except FileNotFoundError:
                content = None

            previous_file = SystemdUnit(unit.path, content)
            previous_files.append(previous_file)

        return previous_files

    def _install_files(self, job: ScheduledJob, unit_files: list[SystemdUnit]) -> None:
        log_path = job.get_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._write_files(unit_files)

    def _write_files(self, unit_files: list[SystemdUnit]) -> None:
        for unit in unit_files:
            self._write_file(unit)

    def _write_file(self, unit: SystemdUnit) -> None:
        if unit.content is None:
            unit.path.unlink(missing_ok=True)

            return

        unit.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = NamedTemporaryFile(dir=unit.path.parent, delete=False)
        temporary_path = Path(temporary_file.name)
        try:
            with temporary_file:
                temporary_file.write(unit.content)

            temporary_path.replace(unit.path)
        finally:
            temporary_path.unlink(missing_ok=True)

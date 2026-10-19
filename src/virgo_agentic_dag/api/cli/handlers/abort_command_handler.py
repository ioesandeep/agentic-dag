"""Terminates a run and removes every host resource that would resume it."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller
from virgo_agentic_dag.domain.infra.agent.session_killer import SessionKiller
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.recovery.recovery_session_killer import (
    RecoverySessionKiller,
)
from virgo_agentic_dag.services.watching.watcher_service import WatcherService
from virgo_agentic_dag.utils.format_label import format_label


class AbortCommandHandler(CommandHandler[AbortCommand]):
    """Terminates a run's watcher, agent sessions, and scheduled job."""

    def __init__(
        self,
        run_lock: RunLock,
        watcher_service: WatcherService,
        session_killer: SessionKiller,
        agent_session_repo: AgentSessionRepo,
        scheduler_factory: SchedulerFactory,
        scheduled_job_repo: ScheduledJobRepo,
        recovery_session_repo: RecoverySessionRepo,
        recovery_session_killer: RecoverySessionKiller,
        extraction_lock: ExtractionLock,
        process_killer: ProcessKiller,
    ) -> None:
        self._run_lock = run_lock
        self._watcher_service = watcher_service
        self._session_killer = session_killer
        self._agent_session_repo = agent_session_repo
        self._scheduler_factory = scheduler_factory
        self._scheduled_job_repo = scheduled_job_repo
        self._recovery_session_repo = recovery_session_repo
        self._recovery_session_killer = recovery_session_killer
        self._extraction_lock = extraction_lock
        self._process_killer = process_killer

    async def handle(self, command: AbortCommand) -> ExitCode:
        await asyncio.to_thread(self._run_lock.acquire_waiting)

        try:
            await self._watcher_service.stop(command.dag_name)
            await self._retire_schedule(command)

            current_time = datetime.now(UTC)
            await self._kill_agents(current_time)
            await self._kill_recovery_session(current_time)
            await self._kill_learning_session()
        finally:
            self._run_lock.release()

        return ExitCode.SUCCESS

    async def _retire_schedule(self, command: AbortCommand) -> None:
        job = await self._scheduled_job_repo.get_by_dag_name(command.dag_name)
        if job is None:
            emit(
                format_label(LABELS["runNotScheduled"], {"dag": command.dag_name})
                + "\n"
            )

            return

        scheduler = self._scheduler_factory.get_scheduler()
        await scheduler.retire(job)
        await self._scheduled_job_repo.delete(job)
        emit(format_label(LABELS["runUnscheduled"], {"job": job.label}) + "\n")

    async def _kill_agents(self, current_time: datetime) -> None:
        sessions = await self._agent_session_repo.get_open_sessions()
        kills = [
            self._session_killer.kill(session, current_time) for session in sessions
        ]
        await asyncio.gather(*kills)

    async def _kill_recovery_session(self, current_time: datetime) -> None:
        recovery_session = await self._recovery_session_repo.find_open_session()
        if recovery_session is None:
            return

        await self._recovery_session_killer.kill(recovery_session, current_time)

    async def _kill_learning_session(self) -> None:
        pid = await asyncio.to_thread(self._extraction_lock.get_session_pid)
        if pid is None:
            return

        self._process_killer.kill(pid)

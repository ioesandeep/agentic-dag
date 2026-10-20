from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)


class RunScheduleService:
    """Maintains the host schedule for a DAG run."""

    def __init__(
        self,
        scheduler: Scheduler,
        scheduled_job_repo: ScheduledJobRepo,
        scheduled_job_builder_factory: Callable[[], ScheduledJobBuilder],
    ) -> None:
        self._scheduler = scheduler
        self._scheduled_job_repo = scheduled_job_repo
        self._scheduled_job_builder_factory = scheduled_job_builder_factory

    async def ensure_registered(self, dag_path: Path) -> ScheduledJob | None:
        """Register a missing host job without replacing an existing host job."""
        current_time = datetime.now(UTC)
        scheduled_job_builder = self._scheduled_job_builder_factory()
        scheduled_job = scheduled_job_builder.build(dag_path, current_time)

        is_registered = await self._scheduler.is_registered(scheduled_job)
        if is_registered:
            stored_job = await self._scheduled_job_repo.get_by_dag_name(
                scheduled_job.dag_name
            )

            if stored_job is None:
                await self._scheduled_job_repo.save(scheduled_job)

            return None

        return await self._register(scheduled_job)

    async def reconcile(self, dag_path: Path) -> ScheduledJob | None:
        """Update the host job when the run's schedule changes."""
        current_time = datetime.now(UTC)
        scheduled_job_builder = self._scheduled_job_builder_factory()
        scheduled_job = scheduled_job_builder.build(dag_path, current_time)

        is_registered = await self._scheduler.is_registered(scheduled_job)
        stored_job = await self._scheduled_job_repo.get_by_dag_name(
            scheduled_job.dag_name
        )

        if is_registered and stored_job is not None:
            is_unchanged = (
                stored_job.argv == scheduled_job.argv
                and stored_job.environment == scheduled_job.environment
                and stored_job.interval_seconds == scheduled_job.interval_seconds
                and stored_job.working_directory == scheduled_job.working_directory
                and stored_job.log_path == scheduled_job.log_path
            )

            if is_unchanged:
                return None

        return await self._register(scheduled_job)

    async def retire(self, dag_name: str) -> None:
        """Stop future passes for a completed or aborted run."""
        stored_job = await self._scheduled_job_repo.get_by_dag_name(dag_name)
        if stored_job is not None:
            await self._scheduled_job_repo.delete(stored_job)

        label = ScheduledJob.get_label(dag_name)
        environment = stored_job.environment if stored_job is not None else "{}"
        scheduled_job = ScheduledJob(
            dag_name=dag_name,
            label=label,
            argv="[]",
            environment=environment,
            interval_seconds=0,
            working_directory="",
            log_path="",
        )

        is_registered = await self._scheduler.is_registered(scheduled_job)
        if is_registered:
            await self._scheduler.retire(scheduled_job)

    async def _register(self, scheduled_job: ScheduledJob) -> ScheduledJob:
        await self._scheduler.register(scheduled_job)
        await self._scheduled_job_repo.save(scheduled_job)

        return scheduled_job

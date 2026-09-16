"""Where the job a host runs for a run is recorded, so a later command can find it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob


class ScheduledJobRepo(ABC):
    """Keeps one row per dag naming the job its host was asked to run."""

    @abstractmethod
    async def save(self, scheduled_job: ScheduledJob) -> None:
        """Record this job, replacing whatever was recorded for its dag before."""

    @abstractmethod
    async def get_by_dag_name(self, dag_name: str) -> ScheduledJob | None:
        """Return the job recorded for this dag, or nothing if none was."""

    @abstractmethod
    async def delete(self, scheduled_job: ScheduledJob) -> None:
        """Delete this job's row after the host has retired it."""

"""The host job-system interface a run registers its recurring pass with."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob


class Scheduler(ABC):
    """Registers and retires jobs with whatever wakes processes on this machine."""

    @abstractmethod
    async def register(self, job: ScheduledJob) -> None:
        """Register this job with the host, replacing any job under its label."""

    @abstractmethod
    async def retire(self, job: ScheduledJob) -> None:
        """Unregister this job from the host."""

    @abstractmethod
    async def is_registered(self, job: ScheduledJob) -> bool:
        """Report whether the host is already running this job."""

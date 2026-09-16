"""Choosing how a run keeps itself woken, so nothing else asks what host it is on."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.host_platform import HostPlatform
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.infra.scheduling.scheduler_type import SchedulerType
from virgo_agentic_dag.infra.scheduling.launchd_scheduler import LaunchdScheduler

LAUNCH_AGENTS_HOME = Path.home() / "Library" / "LaunchAgents"

_SCHEDULER_TYPES: Mapping[HostPlatform, SchedulerType] = {
    HostPlatform.MAC: SchedulerType.LAUNCHD,
    HostPlatform.LINUX: SchedulerType.CRON,
}


class SchedulerFactory:
    """Hands back the scheduler that speaks to this host's own job system."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    def get_scheduler(self) -> Scheduler:
        """Return the scheduler for this host, raising ConfigError when none is built."""
        host_platform = HostPlatform.current()
        scheduler_type = _SCHEDULER_TYPES.get(host_platform)

        if scheduler_type is None:
            raise ConfigError(f"no job system is known for {host_platform.value}")

        if scheduler_type is SchedulerType.LAUNCHD:
            return LaunchdScheduler(
                self._command_runner, LAUNCH_AGENTS_HOME, os.getuid()
            )

        raise ConfigError(f"the {scheduler_type.value} scheduler is not built yet")

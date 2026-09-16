"""The host job system a run registers its recurring pass with."""

from __future__ import annotations

from enum import Enum


class SchedulerType(Enum):
    # macOS user agents, one plist per job
    LAUNCHD = "launchd"
    # the universal Unix timer, one crontab line per job
    CRON = "cron"
    # Linux user timers, which need lingering enabled on a host nobody logs into
    SYSTEMD = "systemd"
    # nothing to register; an orchestrator invokes dagctl on its own cadence
    EXTERNAL = "external"

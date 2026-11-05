"""The factory that returns the sleep inhibitor for this host's operating system."""

from __future__ import annotations

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.host.sleep_inhibitor import SleepInhibitor
from virgo_agentic_dag.domain.infra.scheduling.host_platform import HostPlatform
from virgo_agentic_dag.infra.host.caffeinate_sleep_inhibitor import (
    CaffeinateSleepInhibitor,
)
from virgo_agentic_dag.infra.host.systemd_sleep_inhibitor import SystemdSleepInhibitor
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class SleepInhibitorFactory:
    """Selects the SleepInhibitor implementation by host operating system."""

    def get_sleep_inhibitor(self) -> SleepInhibitor:
        """Return the sleep inhibitor for this host's operating system."""
        host_platform = HostPlatform.current()
        if host_platform is HostPlatform.MAC:
            return CaffeinateSleepInhibitor()

        if host_platform is HostPlatform.LINUX:
            return SystemdSleepInhibitor()

        message = format_label(
            LABELS["sleepInhibitorUnknown"], {"platform": host_platform.value}
        )

        raise ConfigError(message)

"""The host operating system, resolved once so nothing else compares platform strings."""

from __future__ import annotations

import sys
from enum import Enum

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError


class HostPlatform(Enum):
    MAC = "darwin"
    LINUX = "linux"
    WINDOWS = "win32"

    @classmethod
    def current(cls) -> HostPlatform:
        """Return the platform this process runs on, raising ConfigError when unrecognized."""
        try:
            return cls(sys.platform)
        except ValueError:
            raise ConfigError(
                f"{sys.platform} is not a platform this controller knows"
            ) from None

"""The port through which the controller keeps the host from sleeping."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SleepInhibitor(ABC):
    """Prevents the host from sleeping while this process runs."""

    @abstractmethod
    def keep_awake(self) -> None:
        """Keep the host from sleeping until this process exits."""

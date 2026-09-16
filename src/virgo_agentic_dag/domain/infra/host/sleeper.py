"""The port that pauses the controller, so waiting logic stays instant under test."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Sleeper(ABC):
    """Pauses execution for a number of seconds."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Pause for the given number of seconds."""

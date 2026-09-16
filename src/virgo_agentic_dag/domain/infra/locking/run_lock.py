"""The exclusive lock that serializes passes over one run."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RunLock(ABC):
    """Acquires and releases the exclusive claim on a run."""

    @abstractmethod
    def acquire(self) -> None:
        """Claim the run, refusing with RunBusy when another pass already holds it."""

    @abstractmethod
    def acquire_waiting(self) -> None:
        """Claim the run once its holder finishes, waiting as long as that takes."""

    @abstractmethod
    def release(self) -> None:
        """Release the run so the next pass can acquire it."""

"""The exclusive lock that serializes passes over one run."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.infra.locking.run_lock_config import RunLockConfig


class RunLock(ABC):
    """Acquires and releases the exclusive claim on a run."""

    @abstractmethod
    def acquire(self) -> None:
        """Claim the run, refusing with RunBusy when another pass already holds it."""

    @abstractmethod
    def acquire_waiting(self) -> None:
        """Claim the run once its holder finishes, waiting as long as that takes."""

    @abstractmethod
    def acquire_lock(self, run_lock_config: RunLockConfig) -> None:
        """Claim the run, waiting without limit when the config's timeout is None and
        raising RunBusy when the run lock remains unavailable through the timeout."""

    @abstractmethod
    def release(self) -> None:
        """Release the run so the next pass can acquire it."""

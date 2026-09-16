"""The log of every execution of the recovery agent, whatever database stores it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)


class RecoverySessionRepo(ABC):
    """Opens and closes recovery execution rows, one explicit write each."""

    @abstractmethod
    async def add(self, recovery_session: RecoverySession) -> None:
        """Record a single recovery execution as it starts."""

    @abstractmethod
    async def close(self, recovery_session: RecoverySession) -> None:
        """Record when this recovery execution ended."""

    @abstractmethod
    async def find_open_session(self) -> RecoverySession | None:
        """Return the recovery execution not yet ended, or None when every row has ended."""

"""The append-only audit history of a run, read by operators and never by the controller."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry


class AuditEntryRepo(ABC):
    """Records what happened to a node and returns the run's history in order."""

    @abstractmethod
    async def save(self, audit_entry: AuditEntry) -> None:
        """Record one transition with the note that explains it."""

    @abstractmethod
    async def get_all(self) -> list[AuditEntry]:
        """Return the run's history in the order it was written."""

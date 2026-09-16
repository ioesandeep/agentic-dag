"""AuditEntryRepo held in a list, for tests and rehearsals that want no database."""

from __future__ import annotations

from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo


class InMemoryAuditEntryRepo(AuditEntryRepo):
    """Keeps audit rows in process memory with the same contract as the real store."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def save(self, audit_entry: AuditEntry) -> None:
        self._entries.append(audit_entry)

    async def get_all(self) -> list[AuditEntry]:
        return list(self._entries)

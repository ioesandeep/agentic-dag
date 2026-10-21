"""Schedules pending nodes to resume after a wait."""

from datetime import datetime

from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo


class NodeWaitService:
    """Defers node execution until a specified resume time."""

    def __init__(self, node_repo: NodeRepo, audit_entry_repo: AuditEntryRepo) -> None:
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo

    async def wait(
        self,
        node_id: str,
        resume_at: datetime,
        note: str,
        current_time: datetime,
    ) -> None:
        """Record a pending wait until the node's resume time."""
        await self._node_repo.update_state(
            node_id, NodeState.PENDING, current_time, resume_at=resume_at
        )

        audit_entry = AuditEntry(
            node_id=node_id,
            state=NodeState.PENDING.value,
            note=note,
            created_at=current_time,
        )

        await self._audit_entry_repo.save(audit_entry)

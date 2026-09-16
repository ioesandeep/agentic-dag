"""Selects failed nodes due for recovery."""

from __future__ import annotations

from datetime import datetime

from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class RecoveryScanService:
    """A service for selecting failed nodes due for recovery."""

    def __init__(
        self,
        node_repo: NodeRepo,
        node_recovery_repo: NodeRecoveryRepo,
        audit_entry_repo: AuditEntryRepo,
    ) -> None:
        self._node_repo = node_repo
        self._node_recovery_repo = node_recovery_repo
        self._audit_entry_repo = audit_entry_repo

    async def get_recoverable_nodes(self, current_time: datetime) -> list[Node]:
        """Return the failed nodes a recovery agent should examine at this time."""
        stopped_nodes = await self._get_stopped_nodes()

        recoverable_nodes: list[Node] = []
        for node in stopped_nodes:
            is_out_of_attempts = node.is_out_of_attempts()
            if is_out_of_attempts:
                await self._record_out_of_attempts(node, current_time)
                continue

            can_recover = node.can_recover()
            if not can_recover:
                continue

            newest_recovery = (
                await self._node_recovery_repo.get_newest_recovery_by_node_id(node.id)
            )
            is_due = newest_recovery is None or newest_recovery.is_due(current_time)
            if is_due:
                recoverable_nodes.append(node)

        return recoverable_nodes

    async def _get_stopped_nodes(self) -> list[Node]:
        stopped_nodes: list[Node] = []
        for state in (NodeState.ERRORED, NodeState.NEEDS_HUMAN, NodeState.RESTING):
            nodes = await self._node_repo.get_nodes_by_state(state)
            stopped_nodes.extend(nodes)

        return stopped_nodes

    async def _record_out_of_attempts(self, node: Node, current_time: datetime) -> None:
        if node.needs_human():
            return

        await self._node_repo.update_state(node.id, NodeState.NEEDS_HUMAN, current_time)

        attempt_count = await self._node_recovery_repo.count_by_node_id(node.id)
        note = format_label(LABELS["outOfRecoveryAttempts"], {"count": attempt_count})
        audit_entry = AuditEntry(
            node_id=node.id,
            state=NodeState.NEEDS_HUMAN.value,
            note=note,
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)

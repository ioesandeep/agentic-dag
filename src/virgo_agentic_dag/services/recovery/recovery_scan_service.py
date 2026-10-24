"""Selects failed nodes due for recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class RecoveryScanService:
    """A service for selecting failed nodes due for recovery."""

    def __init__(
        self,
        node_repo: NodeRepo,
        node_recovery_repo: NodeRecoveryRepo,
        audit_entry_repo: AuditEntryRepo,
        recovery_session_repo: RecoverySessionRepo,
        dag_spec: DagSpec,
    ) -> None:
        self._node_repo = node_repo
        self._node_recovery_repo = node_recovery_repo
        self._audit_entry_repo = audit_entry_repo
        self._recovery_session_repo = recovery_session_repo
        self._dag_spec = dag_spec

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

            is_due = await self._is_due(node, current_time)
            if is_due:
                recoverable_nodes.append(node)

        return recoverable_nodes

    async def _is_due(self, node: Node, current_time: datetime) -> bool:
        latest_session = node.get_latest_session()
        if latest_session is None:
            return False

        newest_recovery = (
            await self._node_recovery_repo.get_newest_recovery_by_session_id(
                latest_session.id
            )
        )

        if newest_recovery is not None:
            is_due = newest_recovery.is_due(current_time)
            if not is_due:
                return False

        retry_at = await self._get_retry_at(node, newest_recovery)

        return retry_at is None or retry_at <= current_time

    async def _get_retry_at(
        self, node: Node, newest_recovery: NodeRecovery | None
    ) -> datetime | None:
        recovery_sessions = await self._get_closed_recovery_sessions(node)
        last_ended_at = None
        delay_seconds = self._dag_spec.tick_interval_seconds

        for recovery_session in recovery_sessions:
            session_started_at = recovery_session.started_at.replace(tzinfo=UTC)
            if newest_recovery is not None:
                detected_at = newest_recovery.detected_at.replace(tzinfo=UTC)
                if detected_at >= session_started_at:
                    break

            last_ended_at = last_ended_at or recovery_session.ended_at
            delay_seconds = min(delay_seconds * 2, 3600)

        if last_ended_at is None:
            return None

        return last_ended_at.replace(tzinfo=UTC) + timedelta(seconds=delay_seconds)

    async def _get_closed_recovery_sessions(self, node: Node) -> list[RecoverySession]:
        latest_session = node.get_latest_session()
        if latest_session is None:
            return []

        started_at = latest_session.started_at.replace(tzinfo=UTC)
        recovery_sessions = await self._recovery_session_repo.get_all()

        closed_recovery_sessions = []
        for recovery_session in recovery_sessions:
            session_started_at = recovery_session.started_at.replace(tzinfo=UTC)
            node_ids = recovery_session.get_node_ids()
            if (
                recovery_session.ended_at is not None
                and session_started_at >= started_at
                and node.id in node_ids
            ):
                closed_recovery_sessions.append(recovery_session)

        return closed_recovery_sessions

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

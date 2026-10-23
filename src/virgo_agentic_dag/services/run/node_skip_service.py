"""Skips a node of a run and returns its stopped descendants to pending."""

from __future__ import annotations

from datetime import datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.events.node_skipped_event import NodeSkippedEvent
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.run.dependent_release_service import (
    DependentReleaseService,
)
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)
from virgo_agentic_dag.utils.format_label import format_label


class NodeSkipService:
    """A service for skipping a node and returning its descendants that need human input without an agent to pending."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        dependent_release_service: DependentReleaseService,
        run_schedule_service: RunScheduleService,
    ) -> None:
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher
        self._dependent_release_service = dependent_release_service
        self._run_schedule_service = run_schedule_service

    async def skip(self, command: SkipCommand, current_time: datetime) -> list[str]:
        """Mark the named node skipped and return the ids of the nodes moved back to pending."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            raise SkipRefused(
                format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id})
            )

        self._ensure_skippable(node)
        is_already_skipped = node.state == NodeState.SKIPPED.value

        await self._record(node, current_time)

        pending_node_ids = await self._dependent_release_service.release(
            node.id, current_time
        )

        if is_already_skipped and not pending_node_ids:
            return []

        scheduled_job = await self._run_schedule_service.ensure_registered(
            command.dag_path
        )

        if scheduled_job is not None:
            message = format_label(LABELS["runScheduled"], {"job": scheduled_job.label})
            emit(message + "\n")

        return pending_node_ids

    def _ensure_skippable(self, node: Node) -> None:
        """Raise when this node is in progress or has merged."""
        if not node.is_skippable():
            in_progress = NodeState(node.state) is NodeState.IN_PROGRESS
            label_name = "nodeStillInProgress" if in_progress else "nodeAlreadyMerged"

            raise SkipRefused(format_label(LABELS[label_name], {"node_id": node.id}))

    async def _record(self, node: Node, current_time: datetime) -> None:
        await self._node_repo.update_state(node.id, NodeState.SKIPPED, current_time)

        audit_entry = AuditEntry(
            node_id=node.id,
            state=NodeState.SKIPPED.value,
            note=LABELS["skippedByHuman"],
            created_at=current_time,
        )

        await self._audit_entry_repo.save(audit_entry)

        node_event = NodeSkippedEvent(
            node_id=node.id,
            type=NotificationType.SKIPPED,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
        )

        self._notification_publisher.publish(node_event)

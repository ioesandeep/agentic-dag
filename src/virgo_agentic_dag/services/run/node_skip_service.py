"""Skips a node of a run and returns its stopped descendants to pending."""

from __future__ import annotations

import asyncio
from datetime import datetime

from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.node_retried_event import NodeRetriedEvent
from virgo_agentic_dag.domain.events.node_skipped_event import NodeSkippedEvent
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.graph_service import GraphService
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class NodeSkipService:
    """A service for skipping a node and returning its descendants that need human input without an agent to pending."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        graph_builder: GraphBuilder,
    ) -> None:
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher
        self._graph_builder = graph_builder

    async def skip(self, command: SkipCommand, current_time: datetime) -> list[str]:
        """Mark the named node skipped and return the ids of the nodes moved back to pending."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            raise SkipRefused(
                format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id})
            )

        self._ensure_skippable(node)

        graph = self._graph_builder.build_from_path(command.dag_path)
        graph_service = GraphService(graph)
        descendants = graph_service.get_descendants(node.id)

        await self._record(
            node,
            NodeState.SKIPPED,
            LABELS["skippedByHuman"],
            NotificationType.SKIPPED,
            current_time,
        )

        return await self._return_to_pending(descendants, current_time)

    def _ensure_skippable(self, node: Node) -> None:
        """Raise when this node is in progress or has merged."""
        if not node.is_skippable():
            in_progress = NodeState(node.state) is NodeState.IN_PROGRESS
            label_name = "nodeStillInProgress" if in_progress else "nodeAlreadyMerged"

            raise SkipRefused(format_label(LABELS[label_name], {"node_id": node.id}))

    async def _return_to_pending(
        self, descendants: list[GraphNode], current_time: datetime
    ) -> list[str]:
        """Move to pending every descendant that stopped before an agent was created for it."""
        descendant_ids = [graph_node.id for graph_node in descendants]
        descendant_nodes = await self._node_repo.get_nodes_by_ids(descendant_ids)
        stopped_nodes = [
            node for node in descendant_nodes if node.needs_human_without_agent()
        ]

        writes = [
            self._record(
                stopped_node,
                NodeState.PENDING,
                LABELS["upstreamSkipped"],
                NotificationType.RETRIED,
                current_time,
            )
            for stopped_node in stopped_nodes
        ]
        await asyncio.gather(*writes)

        return [stopped_node.id for stopped_node in stopped_nodes]

    async def _record(
        self,
        node: Node,
        state: NodeState,
        note: str,
        notification_type: NotificationType,
        current_time: datetime,
    ) -> None:
        """Records a node state change."""
        await self._node_repo.update_state(node.id, state, current_time)

        audit_entry = AuditEntry(
            node_id=node.id, state=state.value, note=note, created_at=current_time
        )
        await self._audit_entry_repo.save(audit_entry)

        node_event = self._get_event(node, notification_type, current_time)
        self._notification_publisher.publish(node_event)

    def _get_event(
        self, node: Node, notification_type: NotificationType, current_time: datetime
    ) -> NodeEvent:
        """Create a skip or retry event for the node."""
        if notification_type is NotificationType.SKIPPED:
            return NodeSkippedEvent(
                node_id=node.id,
                type=notification_type,
                created_at=current_time,
                updated_at=current_time,
                title=node.title,
                agent_name=node.get_agent_name(),
            )

        return NodeRetriedEvent(
            node_id=node.id,
            type=notification_type,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
        )

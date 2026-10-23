from datetime import datetime

from virgo_agentic_dag.domain.events.node_retried_event import NodeRetriedEvent
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_service import GraphService
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class DependentReleaseService:
    """Return dependents stopped by an upstream failure to pending."""

    def __init__(
        self,
        graph: Graph,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
    ) -> None:
        self._graph = graph
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher

    async def release(self, node_id: str, current_time: datetime) -> list[str]:
        """Return unstarted dependents to pending after an upstream node restarts or is skipped."""
        graph_service = GraphService(self._graph)
        descendants = graph_service.get_descendants(node_id)
        descendant_ids = [graph_node.id for graph_node in descendants]
        descendant_nodes = await self._node_repo.get_nodes_by_ids(descendant_ids)

        stopped_nodes = await self._get_stopped_nodes(descendant_nodes)
        for node in stopped_nodes:
            await self._record(node, current_time)

        return [node.id for node in stopped_nodes]

    async def _get_stopped_nodes(self, nodes: list[Node]) -> list[Node]:
        upstream_stopped_notes = {
            format_label(LABELS["upstreamStopped"], {"node_id": graph_node.id})
            for graph_node in self._graph.nodes
        }

        audit_entries = await self._audit_entry_repo.get_all()
        latest_notes = {entry.node_id: entry.note for entry in audit_entries}

        stopped_nodes = []
        for node in nodes:
            needs_human_without_agent = node.needs_human_without_agent()
            latest_note = latest_notes.get(node.id)
            if needs_human_without_agent and latest_note in upstream_stopped_notes:
                stopped_nodes.append(node)

        return stopped_nodes

    async def _record(self, node: Node, current_time: datetime) -> None:
        await self._node_repo.update_state(node.id, NodeState.PENDING, current_time)

        audit_entry = AuditEntry(
            node_id=node.id,
            state=NodeState.PENDING.value,
            note=LABELS["upstreamSkipped"],
            created_at=current_time,
        )

        await self._audit_entry_repo.save(audit_entry)

        node_event = NodeRetriedEvent(
            node_id=node.id,
            type=NotificationType.RETRIED,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
        )

        self._notification_publisher.publish(node_event)

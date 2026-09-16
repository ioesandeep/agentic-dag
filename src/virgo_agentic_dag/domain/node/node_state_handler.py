"""The handler interface for advancing the nodes in one run state."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.tick.tick_response import TickResponse


class NodeStateHandler(ABC):
    """Advances the nodes in one run state and records each transition."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
    ) -> None:
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher

    @abstractmethod
    async def handle(
        self,
        graph: Graph,
        graph_nodes: list[GraphNode],
        current_time: datetime,
        /,
    ) -> TickResponse:
        """Advance this state's nodes, reading whatever run state the decision needs."""

    async def record(self, node_event: NodeEvent, state: NodeState, note: str) -> None:
        """Move a node to a new state everywhere the run is recorded and read."""
        current_time = node_event.created_at
        await self._node_repo.update_state(node_event.node_id, state, current_time)

        audit_entry = AuditEntry(
            node_id=node_event.node_id,
            state=state.value,
            note=note,
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)

        self._notification_publisher.publish(node_event)

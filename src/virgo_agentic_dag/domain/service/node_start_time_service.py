"""Calculates start times for graph nodes with cooldowns."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.service.graph_service import GraphService


class NodeStartTimeService:
    """A service for calculating when graph nodes may start after their dependencies."""

    def __init__(self, graph: Graph) -> None:
        self._graph_service = GraphService(graph)

    def get_start_time(
        self, graph_node: GraphNode, nodes: list[Node]
    ) -> datetime | None:
        """Return the node's start time, or None when no cooldown is active."""
        if not graph_node.cooldown_seconds:
            return None

        skipped_nodes = [
            node for node in nodes if node.state == NodeState.SKIPPED.value
        ]
        declared_dependencies = self._graph_service.get_dependencies(graph_node.id)
        effective_dependencies = self._graph_service.get_effective_dependencies(
            graph_node.id, skipped_nodes
        )
        dependency_ids = {
            dependency.id
            for dependency in [*declared_dependencies, *effective_dependencies]
        }

        merged_or_skipped_times = [
            node.updated_at.replace(tzinfo=UTC)
            for node in nodes
            if node.id in dependency_ids and node.is_merged_or_skipped()
        ]
        if not merged_or_skipped_times:
            return None

        cooldown = timedelta(seconds=graph_node.cooldown_seconds)

        return max(merged_or_skipped_times) + cooldown

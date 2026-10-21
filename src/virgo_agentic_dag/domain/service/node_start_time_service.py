"""Calculates when pending nodes may start."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.service.graph_service import GraphService


class NodeStartTimeService:
    """Calculates node start times for cooldowns and scheduled waits."""

    def __init__(self, graph: Graph) -> None:
        self._graph_service = GraphService(graph)

    def get_start_time(
        self, graph_node: GraphNode, nodes: list[Node]
    ) -> datetime | None:
        """Return the earliest time the node may start."""
        start_times = [
            node.resume_at.replace(tzinfo=UTC)
            for node in nodes
            if node.id == graph_node.id and node.resume_at is not None
        ]

        cooldown_start_time = self._get_cooldown_start_time(graph_node, nodes)
        if cooldown_start_time is not None:
            start_times.append(cooldown_start_time)

        return max(start_times, default=None)

    def _get_cooldown_start_time(
        self, graph_node: GraphNode, nodes: list[Node]
    ) -> datetime | None:
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

"""Queries one graph against the node state the caller supplies."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.node.node_state import NodeState


class GraphService:
    """Queries one graph against node state supplied per call, caching nothing."""

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._graph_nodes_by_id = {
            graph_node.id: graph_node for graph_node in graph.nodes
        }

    def get_pending_nodes(self, nodes: list[Node]) -> list[GraphNode]:
        """Return the nodes waiting to start, in graph order."""
        return self._nodes_in(NodeState.PENDING, nodes)

    def get_in_progress_nodes(self, nodes: list[Node]) -> list[GraphNode]:
        """Return the nodes whose agents are working, in graph order."""
        return self._nodes_in(NodeState.IN_PROGRESS, nodes)

    def get_resting_nodes(self, nodes: list[Node]) -> list[GraphNode]:
        """Return the nodes waiting on their pull requests, in graph order."""
        return self._nodes_in(NodeState.RESTING, nodes)

    def get_merged_nodes(self, nodes: list[Node]) -> list[GraphNode]:
        """Return the nodes whose pull requests have merged, in graph order."""
        return self._nodes_in(NodeState.MERGED, nodes)

    def get_dependencies(self, node_id: str) -> list[GraphNode]:
        """Return the nodes this one directly depends on."""
        graph_node = self._graph_nodes_by_id.get(node_id)
        if graph_node is None:
            return []

        return [
            self._graph_nodes_by_id[dep_id]
            for dep_id in graph_node.depends_on
            if dep_id in self._graph_nodes_by_id
        ]

    def get_effective_dependencies(
        self, node_id: str, skipped_nodes: list[Node]
    ) -> list[GraphNode]:
        """Return the dependencies of this node, with each skipped dependency replaced by its own dependencies."""
        skipped_ids = {node.id for node in skipped_nodes}
        effective_dependency_ids: set[str] = set()
        resolved_ids: set[str] = set()
        frontier = [dependency.id for dependency in self.get_dependencies(node_id)]

        while frontier:
            dependency_id = frontier.pop()
            if dependency_id in resolved_ids:
                continue

            resolved_ids.add(dependency_id)
            if dependency_id not in skipped_ids:
                effective_dependency_ids.add(dependency_id)
                continue

            inherited_dependencies = self.get_dependencies(dependency_id)
            frontier += [dependency.id for dependency in inherited_dependencies]

        return self._graph_nodes_with_ids(effective_dependency_ids)

    def get_descendants(self, node_id: str) -> list[GraphNode]:
        """Return every node that depends on this one, directly or through another."""
        descendant_ids: set[str] = set()
        frontier = [node_id]

        while frontier:
            current_id = frontier.pop()
            for graph_node in self._graph.nodes:
                if current_id not in graph_node.depends_on:
                    continue

                if graph_node.id in descendant_ids:
                    continue

                descendant_ids.add(graph_node.id)
                frontier.append(graph_node.id)

        return self._graph_nodes_with_ids(descendant_ids)

    def is_complete(self, nodes: list[Node]) -> bool:
        """Report whether every node has reached a state the controller never leaves."""
        terminal_ids = {
            node.id for node in nodes if NodeState(node.state).is_terminal()
        }

        return all(graph_node.id in terminal_ids for graph_node in self._graph.nodes)

    def _nodes_in(self, state: NodeState, nodes: list[Node]) -> list[GraphNode]:
        matching_ids = {node.id for node in nodes if node.state == state.value}

        return self._graph_nodes_with_ids(matching_ids)

    def _graph_nodes_with_ids(self, node_ids: set[str]) -> list[GraphNode]:
        return [
            graph_node for graph_node in self._graph.nodes if graph_node.id in node_ids
        ]

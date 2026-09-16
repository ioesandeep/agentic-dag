"""The facade a control pass dispatches each node state through."""

from __future__ import annotations

from datetime import datetime

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.node.node_state_handler import NodeStateHandler
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.graph_service import GraphService
from virgo_agentic_dag.domain.tick.tick_response import TickResponse


class NodeStateHandlingFacade:
    """Dispatches one run state per call to its handler, on freshly read rows."""

    def __init__(
        self,
        node_repo: NodeRepo,
        in_progress_handler: NodeStateHandler,
        resting_handler: NodeStateHandler,
        pending_handler: NodeStateHandler,
        merged_handler: NodeStateHandler,
    ) -> None:
        self._node_repo = node_repo
        self._in_progress_handler = in_progress_handler
        self._resting_handler = resting_handler
        self._pending_handler = pending_handler
        self._merged_handler = merged_handler

    async def handle_in_progress_nodes(
        self, graph: Graph, current_time: datetime
    ) -> TickResponse:
        """Sweep the nodes whose agents are working."""
        graph_service = GraphService(graph)
        nodes = await self._node_repo.get_nodes_by_state(NodeState.IN_PROGRESS)
        graph_nodes = graph_service.get_in_progress_nodes(nodes)

        return await self._in_progress_handler.handle(graph, graph_nodes, current_time)

    async def handle_resting_nodes(
        self, graph: Graph, current_time: datetime
    ) -> TickResponse:
        """Sweep the nodes waiting on their pull requests."""
        graph_service = GraphService(graph)
        nodes = await self._node_repo.get_nodes_by_state(NodeState.RESTING)
        graph_nodes = graph_service.get_resting_nodes(nodes)

        return await self._resting_handler.handle(graph, graph_nodes, current_time)

    async def handle_pending_nodes(
        self, graph: Graph, current_time: datetime
    ) -> TickResponse:
        """Sweep the nodes waiting to start."""
        graph_service = GraphService(graph)
        nodes = await self._node_repo.get_nodes_by_state(NodeState.PENDING)
        graph_nodes = graph_service.get_pending_nodes(nodes)

        return await self._pending_handler.handle(graph, graph_nodes, current_time)

    async def handle_merged_nodes(
        self, graph: Graph, current_time: datetime
    ) -> TickResponse:
        """Sweep the nodes whose pull requests have merged."""
        graph_service = GraphService(graph)
        nodes = await self._node_repo.get_nodes_by_state(NodeState.MERGED)
        graph_nodes = graph_service.get_merged_nodes(nodes)

        return await self._merged_handler.handle(graph, graph_nodes, current_time)

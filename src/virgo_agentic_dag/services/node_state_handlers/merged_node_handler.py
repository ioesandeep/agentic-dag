"""Advances a node whose pull request has merged."""

from __future__ import annotations

import logging
from datetime import datetime

from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state_handler import NodeStateHandler
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.tick.tick_response import TickResponse

logger = logging.getLogger(__name__)


class MergedNodeHandler(NodeStateHandler):
    """Reclaims the working copy of every node whose pull request has merged."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        node_agent_repo: NodeAgentRepo,
        work_tree_repo: WorkTreeRepo,
        workspace: Workspace,
    ) -> None:
        super().__init__(node_repo, audit_entry_repo, notification_publisher)
        self._node_agent_repo = node_agent_repo
        self._work_tree_repo = work_tree_repo
        self._workspace = workspace

    async def handle(
        self,
        graph: Graph,
        merged_graph_nodes: list[GraphNode],
        current_time: datetime,
    ) -> TickResponse:
        tick_response = TickResponse()
        for graph_node in merged_graph_nodes:
            node_response = await self._advance(graph_node, current_time)
            tick_response = tick_response.increment_with(node_response)

        return tick_response

    async def _advance(
        self, graph_node: GraphNode, current_time: datetime
    ) -> TickResponse:
        agent = await self._node_agent_repo.get_by_node_id(graph_node.id)
        if agent is None or agent.worktree is None:
            return TickResponse()

        worktree = agent.worktree
        if worktree.reclaimed_at is not None:
            return TickResponse()

        try:
            await self._workspace.remove(worktree)
        except (WorktreeError, OSError) as error:
            logger.warning(
                "%s keeps its worktree, reclaiming retries next tick: %s",
                graph_node.id,
                error,
            )

            return TickResponse()

        reclaimed_worktree = WorkTree(
            id=worktree.id,
            agent_id=worktree.agent_id,
            name=worktree.name,
            absolute_path=worktree.absolute_path,
            branch=worktree.branch,
            pr_number=worktree.pr_number,
            marks=worktree.marks,
            created_at=worktree.created_at,
            reclaimed_at=current_time,
        )
        await self._work_tree_repo.mark_reclaimed(reclaimed_worktree)
        logger.info("reclaimed the worktree of %s", graph_node.id)

        return TickResponse()

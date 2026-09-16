"""Advances a node that has not yet started."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.node.node_state_handler import NodeStateHandler
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_service import GraphService
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.run.node_importer import NodeImporter
from virgo_agentic_dag.utils.create_session_token import create_session_token
from virgo_agentic_dag.utils.format_label import format_label

logger = logging.getLogger(__name__)

_STOPPED = (NodeState.NEEDS_HUMAN, NodeState.ERRORED)


class PendingNodeHandler(NodeStateHandler):
    """Starts or adopts each pending node once its dependencies, budget, and executor allow."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        workspace: Workspace,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
        dag_spec: DagSpec,
        node_agent_repo: NodeAgentRepo,
        code_repo: CodeRepo,
        node_importer: NodeImporter,
    ) -> None:
        super().__init__(node_repo, audit_entry_repo, notification_publisher)
        self._workspace = workspace
        self._agent_launchers = agent_launchers
        self._dag_spec = dag_spec
        self._node_agent_repo = node_agent_repo
        self._code_repo = code_repo
        self._node_importer = node_importer

    async def handle(
        self,
        graph: Graph,
        pending_graph_nodes: list[GraphNode],
        current_time: datetime,
    ) -> TickResponse:
        tick_response = TickResponse()
        for graph_node in pending_graph_nodes:
            node_response = await self._advance(graph, graph_node, current_time)
            tick_response = tick_response.increment_with(node_response)

        return tick_response

    async def _advance(
        self,
        graph: Graph,
        graph_node: GraphNode,
        current_time: datetime,
    ) -> TickResponse:
        graph_service = GraphService(graph)
        skipped_nodes = await self._node_repo.get_nodes_by_state(NodeState.SKIPPED)
        dependencies = graph_service.get_effective_dependencies(
            graph_node.id, skipped_nodes
        )

        dependency_ids = [dependency.id for dependency in dependencies]
        dependency_nodes = await self._node_repo.get_nodes_by_ids(dependency_ids)

        stopped_dependency = next(
            (node for node in dependency_nodes if NodeState(node.state) in _STOPPED),
            None,
        )
        if stopped_dependency is not None:
            note = format_label(
                LABELS["upstreamStopped"], {"node_id": stopped_dependency.id}
            )
            node_event = self._get_stopped_event(
                graph_node,
                NotificationType.NEEDS_HUMAN,
                note,
                current_time,
            )
            await self.record(node_event, NodeState.NEEDS_HUMAN, note)

            return TickResponse(events_applied=1)

        dependency_states = [NodeState(node.state) for node in dependency_nodes]
        if not all(state is NodeState.MERGED for state in dependency_states):
            return TickResponse()

        in_progress_nodes = await self._node_repo.get_nodes_by_state(
            NodeState.IN_PROGRESS
        )
        if len(in_progress_nodes) >= self._dag_spec.max_workers:
            return TickResponse()

        executor_agent = graph_node.executor_agent
        agent_name = executor_agent.value if executor_agent else "none"
        launcher = self._agent_launchers.get(executor_agent) if executor_agent else None

        if launcher is None:
            note = format_label(LABELS["unknownExecutor"], {"executor": agent_name})
            node_event = self._get_stopped_event(
                graph_node, NotificationType.NEEDS_HUMAN, note, current_time
            )
            await self.record(node_event, NodeState.NEEDS_HUMAN, note)

            return TickResponse(events_applied=1)

        try:
            if graph_node.is_adopted():
                return await self._adopt(graph_node)

            return await self._start(graph_node, agent_name, launcher, current_time)
        except (WorktreeError, ObservationError, OSError) as error:
            logger.warning(
                "%s stays pending, it will retry next tick: %s", graph_node.id, error
            )

            return TickResponse()

    async def _adopt(self, graph_node: GraphNode) -> TickResponse:
        pr_details = await self._code_repo.get_pr_details_from_url(graph_node.pr)
        await self._node_importer.import_node(graph_node, pr_details)

        return TickResponse(events_applied=1, sessions_started=1)

    async def _start(
        self,
        graph_node: GraphNode,
        agent_product: str,
        launcher: AgentLauncher,
        current_time: datetime,
    ) -> TickResponse:
        node = await self._node_repo.read(graph_node.id)
        if node is None:
            return TickResponse()

        worktree = await self._workspace.provision(graph_node)
        recorded_agent = await self._node_agent_repo.get_by_node_id(graph_node.id)
        if recorded_agent is not None and recorded_agent.resume_token:
            agent = recorded_agent
            session = await launcher.wake(graph_node, LABELS["retryMessage"], agent)
        else:
            agent = self._create_agent(
                graph_node, agent_product, worktree, recorded_agent
            )
            session = await launcher.launch(graph_node, graph_node.instructions, agent)

        agent.sessions.append(session)
        await self._node_agent_repo.save(agent)

        note = format_label(
            LABELS["workStarted"], {"agent_name": node.get_agent_name()}
        )
        node_event = WorkStartedEvent(
            node_id=graph_node.id,
            type=NotificationType.WORK_STARTED,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
        )
        await self.record(node_event, NodeState.IN_PROGRESS, note)

        return TickResponse(events_applied=1, sessions_started=1)

    def _get_stopped_event(
        self,
        graph_node: GraphNode,
        notification_type: NotificationType,
        reason: str,
        current_time: datetime,
    ) -> AgentStoppedEvent:
        """Create an event for an agent stop on the pending graph node."""
        return AgentStoppedEvent(
            node_id=graph_node.id,
            type=notification_type,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
            reason=reason,
        )

    def _create_agent(
        self,
        graph_node: GraphNode,
        agent_product: str,
        worktree: WorkTree,
        recorded_agent: NodeAgent | None,
    ) -> NodeAgent:
        """Creates an agent for the graph node, keeping the identity and history of a recorded one."""
        resume_token = create_session_token()
        if recorded_agent is None:
            return NodeAgent(
                id=str(uuid.uuid4()),
                name=Path(agent_product).name,
                resume_token=resume_token,
                node_id=graph_node.id,
                worktree=worktree,
            )

        return NodeAgent(
            id=recorded_agent.id,
            name=Path(agent_product).name,
            resume_token=resume_token,
            node_id=graph_node.id,
            sessions=[*recorded_agent.sessions],
            worktree=recorded_agent.worktree,
        )

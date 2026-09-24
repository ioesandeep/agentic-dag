"""Stops an in-progress node's running session."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from virgo_agentic_dag.config.constants import STOPPED_SESSION_END_STATE
from virgo_agentic_dag.domain.command.stop_command import StopCommand
from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.exceptions.run.stop_refused import StopRefused
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class NodeStopService:
    """A service for stopping an in-progress node and moving it to NEEDS_HUMAN."""

    def __init__(
        self,
        node_repo: NodeRepo,
        agent_session_repo: AgentSessionRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        graph_builder: GraphBuilder,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
    ) -> None:
        self._node_repo = node_repo
        self._agent_session_repo = agent_session_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher
        self._graph_builder = graph_builder
        self._agent_launchers = agent_launchers

    async def stop(self, command: StopCommand, current_time: datetime) -> None:
        """Stop the specified node's running session."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            raise StopRefused(
                format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id})
            )

        self._ensure_in_progress(node)

        is_process_dead = node.is_process_dead()
        latest_session = node.get_latest_session()
        worktree = node.agent.worktree if node.agent is not None else None
        if is_process_dead or latest_session is None or worktree is None:
            raise StopRefused(
                format_label(LABELS["nodeSessionNotRunning"], {"node_id": node.id})
            )

        launcher = self._get_launcher(command)
        await launcher.stop(latest_session)

        await self._close_session(latest_session, worktree, current_time)
        await self._move_to_needs_human(node, current_time)

    def _ensure_in_progress(self, node: Node) -> None:
        """Raise `StopRefused` when the node is not in progress."""
        state = NodeState(node.state)
        if state is not NodeState.IN_PROGRESS:
            values = {"node_id": node.id, "state": state.value}

            raise StopRefused(format_label(LABELS["nodeNotInProgress"], values))

    def _get_launcher(self, command: StopCommand) -> AgentLauncher:
        """Return the launcher for the node's executor agent."""
        graph = self._graph_builder.build_from_path(command.dag_path)
        graph_node = next(
            (
                graph_node
                for graph_node in graph.nodes
                if graph_node.id == command.node_id
            ),
            None,
        )
        if graph_node is None or graph_node.executor_agent is None:
            raise StopRefused(
                format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id})
            )

        return self._agent_launchers[graph_node.executor_agent]

    async def _close_session(
        self, session: AgentSession, worktree: WorkTree, current_time: datetime
    ) -> None:
        """Close the session with the stopped end state."""
        exit_code = worktree.find_exit_code()
        log_tail = worktree.find_log_tail()
        closed_session = AgentSession(
            id=session.id,
            agent_id=session.agent_id,
            started_at=session.started_at,
            ended_at=current_time,
            end_state=STOPPED_SESSION_END_STATE,
            triggered_by=session.triggered_by,
            pid=session.pid,
            pid_start=session.pid_start,
            exit_code=exit_code,
            log_tail=log_tail,
        )
        await self._agent_session_repo.close(closed_session)

    async def _move_to_needs_human(self, node: Node, current_time: datetime) -> None:
        """Move the node to `NEEDS_HUMAN`."""
        await self._node_repo.update_state(node.id, NodeState.NEEDS_HUMAN, current_time)

        note = LABELS["stoppedByPerson"]
        audit_entry = AuditEntry(
            node_id=node.id,
            state=NodeState.NEEDS_HUMAN.value,
            note=note,
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)

        node_event = AgentStoppedEvent(
            node_id=node.id,
            type=NotificationType.NEEDS_HUMAN,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
            reason=note,
        )
        self._notification_publisher.publish(node_event)

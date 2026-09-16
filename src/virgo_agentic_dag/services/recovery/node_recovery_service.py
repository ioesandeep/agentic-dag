"""Applies the recovery agent's decision to a node and records it."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.recover_command import RecoverCommand
from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

_WAKEABLE = (NodeState.ERRORED, NodeState.NEEDS_HUMAN, NodeState.RESTING)


class NodeRecoveryService:
    """Restores, resumes and records one failed node, so every decision leaves a row behind."""

    def __init__(
        self,
        node_repo: NodeRepo,
        node_recovery_repo: NodeRecoveryRepo,
        agent_session_repo: AgentSessionRepo,
        audit_entry_repo: AuditEntryRepo,
        work_tree_repo: WorkTreeRepo,
        notification_publisher: NotificationPublisher,
        graph_builder: GraphBuilder,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
    ) -> None:
        self._node_repo = node_repo
        self._node_recovery_repo = node_recovery_repo
        self._agent_session_repo = agent_session_repo
        self._audit_entry_repo = audit_entry_repo
        self._work_tree_repo = work_tree_repo
        self._notification_publisher = notification_publisher
        self._graph_builder = graph_builder
        self._agent_launchers = agent_launchers

    async def recover(self, command: RecoverCommand) -> ExitCode:
        """Apply what the recovery agent decided and record the failure, or change nothing."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            emit(format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id}))

            return ExitCode.FAILURE

        latest_session = node.get_latest_session()
        if latest_session is None:
            emit(format_label(LABELS["nodeHasNoSession"], {"node_id": node.id}))

            return ExitCode.FAILURE

        if command.restore_marks and not await self._restore_marks(
            node, latest_session
        ):
            return ExitCode.FAILURE

        if command.wake_message and not await self._wake(node, command, latest_session):
            return ExitCode.FAILURE

        await self._record(node, command, latest_session)

        return ExitCode.SUCCESS

    async def _record(
        self, node: Node, command: RecoverCommand, latest_session: AgentSession
    ) -> None:
        """Write this failure and verdict, leaving an unrecoverable node to a human."""
        current_time = datetime.now(UTC)
        recover_at = command.recover_at or current_time
        node_recovery = NodeRecovery(
            node_id=node.id,
            session_id=latest_session.id,
            detected_at=current_time,
            cause=command.cause.value,
            recoverable=command.recoverable,
            recover_at=recover_at,
            action=command.action,
        )
        await self._node_recovery_repo.add(node_recovery)

        if not command.recoverable and not node.needs_human():
            note = format_label(
                LABELS["markedUnrecoverable"],
                {"cause": command.cause.value, "action": command.action},
            )
            await self._move(
                node,
                NodeState.NEEDS_HUMAN,
                note,
                NotificationType.NEEDS_HUMAN,
                reason=note,
            )

        values = {
            "node_id": node.id,
            "cause": command.cause.value,
            "recoverable": command.recoverable,
            "recover_at": recover_at,
        }
        emit(format_label(LABELS["recoveryRecorded"], values))

    async def _restore_marks(self, node: Node, latest_session: AgentSession) -> bool:
        """Put this worktree's watermarks back to the latest session's, reporting whether it happened."""
        if latest_session.is_process_alive():
            self._report_process_alive(node, latest_session)

            return False

        worktree = node.agent.worktree if node.agent is not None else None
        marks_before = latest_session.marks_before
        if worktree is None or marks_before is None:
            emit(format_label(LABELS["noMarksBefore"], {"node_id": node.id}))

            return False

        restored_worktree = WorkTree(
            id=worktree.id,
            agent_id=worktree.agent_id,
            name=worktree.name,
            absolute_path=worktree.absolute_path,
            branch=worktree.branch,
            pr_number=worktree.pr_number,
            marks=marks_before,
            created_at=worktree.created_at,
            reclaimed_at=worktree.reclaimed_at,
        )
        await self._work_tree_repo.advance_marks(restored_worktree)

        values = {"node_id": node.id, "marks": marks_before}
        emit(format_label(LABELS["marksRestored"], values))

        return True

    async def _wake(
        self, node: Node, command: RecoverCommand, latest_session: AgentSession
    ) -> bool:
        """Resume this node's conversation with the message, reporting whether it started."""
        state = NodeState(node.state)
        if state not in _WAKEABLE:
            values = {"node_id": node.id, "state": state.value}
            emit(format_label(LABELS["nodeNotWakeable"], values))

            return False

        if latest_session.is_process_alive():
            self._report_process_alive(node, latest_session)

            return False

        agent = node.agent
        if agent is None or agent.worktree is None or not agent.resume_token:
            emit(format_label(LABELS["nodeHasNoConversation"], {"node_id": node.id}))

            return False

        graph_node = self._find_graph_node(command)
        launcher = self._find_launcher(graph_node)
        if graph_node is None or launcher is None:
            emit(format_label(LABELS["nodeNotInRun"], {"node_id": node.id}))

            return False

        try:
            session = await launcher.wake(graph_node, command.wake_message, agent)
        except (WorktreeError, OSError) as error:
            values = {"node_id": node.id, "error": str(error)}
            emit(format_label(LABELS["wakeFailed"], values))

            return False

        await self._agent_session_repo.add(session)

        note = format_label(
            LABELS["wokenByRecovery"], {"message": command.wake_message}
        )
        await self._move(
            node, NodeState.IN_PROGRESS, note, NotificationType.WORK_STARTED
        )
        emit(format_label(LABELS["nodeWoken"], {"node_id": node.id}))

        return True

    def _report_process_alive(self, node: Node, session: AgentSession) -> None:
        values = {"node_id": node.id, "pid": session.pid}
        emit(format_label(LABELS["nodeProcessAlive"], values))

    def _find_graph_node(self, command: RecoverCommand) -> GraphNode | None:
        graph = self._graph_builder.build_from_path(command.dag_path)

        return next((node for node in graph.nodes if node.id == command.node_id), None)

    def _find_launcher(self, graph_node: GraphNode | None) -> AgentLauncher | None:
        if graph_node is None or graph_node.executor_agent is None:
            return None

        return self._agent_launchers.get(graph_node.executor_agent)

    async def _move(
        self,
        node: Node,
        state: NodeState,
        note: str,
        notification_type: NotificationType,
        reason: str = "",
    ) -> None:
        """Move this node to a new state everywhere the run is recorded and read."""
        current_time = datetime.now(UTC)

        await self._node_repo.update_state(node.id, state, current_time)

        audit_entry = AuditEntry(
            node_id=node.id, state=state.value, note=note, created_at=current_time
        )
        await self._audit_entry_repo.save(audit_entry)

        node_event = self._get_event(node, notification_type, reason, current_time)
        self._notification_publisher.publish(node_event)

    def _get_event(
        self,
        node: Node,
        notification_type: NotificationType,
        reason: str,
        current_time: datetime,
    ) -> NodeEvent:
        """Create a node event for a recovery state change."""
        if notification_type is NotificationType.WORK_STARTED:
            return WorkStartedEvent(
                node_id=node.id,
                type=notification_type,
                created_at=current_time,
                updated_at=current_time,
                title=node.title,
                agent_name=node.get_agent_name(),
            )

        return AgentStoppedEvent(
            node_id=node.id,
            type=notification_type,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
            reason=reason,
        )

"""Runs the `retry` command, returning a stopped node to the run as pending."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.retry_command import RetryCommand
from virgo_agentic_dag.domain.events.node_retried_event import NodeRetriedEvent
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.locking.run_lock_config import RunLockConfig
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

_RETRYABLE = (NodeState.ERRORED, NodeState.NEEDS_HUMAN)


class RetryCommandHandler(CommandHandler[RetryCommand]):
    """Sends a stopped node back to pending, so the next pass starts it again."""

    def __init__(
        self,
        run_lock: RunLock,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        node_agent_repo: NodeAgentRepo,
    ) -> None:
        self._run_lock = run_lock
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher
        self._node_agent_repo = node_agent_repo

    async def handle(self, command: RetryCommand) -> ExitCode:
        run_lock_config = RunLockConfig(timeout=command.timeout)
        await asyncio.to_thread(self._run_lock.acquire_lock, run_lock_config)

        try:
            return await self._retry(command)
        finally:
            self._run_lock.release()

    async def _retry(self, command: RetryCommand) -> ExitCode:
        """Put the named node back in the run, refusing one the controller has not given up."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            emit(format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id}))

            return ExitCode.FAILURE

        state = NodeState(node.state)
        if state not in _RETRYABLE:
            emit(
                format_label(
                    LABELS["nodeNotStopped"],
                    {"node_id": node.id, "state": state.value},
                )
            )

            return ExitCode.FAILURE

        if command.reset:
            await self._clear_resume_token(node)

        await self._record(node)
        emit(format_label(LABELS["nodeRetried"], {"node_id": node.id}))

        return ExitCode.SUCCESS

    async def _clear_resume_token(self, node: Node) -> None:
        """Drop the recorded conversation of this node's agent, so the next start opens a new one."""
        agent = await self._node_agent_repo.get_by_node_id(node.id)
        if agent is None:
            return

        reset_agent = NodeAgent(
            id=agent.id,
            name=agent.name,
            resume_token="",
            node_id=agent.node_id,
            sessions=[*agent.sessions],
            worktree=agent.worktree,
        )
        await self._node_agent_repo.save(reset_agent)

    async def _record(self, node: Node) -> None:
        """Move this node to pending everywhere the run is recorded and read."""
        current_time = datetime.now(UTC)

        await self._node_repo.update_state(node.id, NodeState.PENDING, current_time)

        audit_entry = AuditEntry(
            node_id=node.id,
            state=NodeState.PENDING.value,
            note=LABELS["sentBackToWork"],
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

"""Starts a recovery agent session for failed nodes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.recovery.recovery_prompt_composer import (
    RecoveryPromptComposer,
)
from virgo_agentic_dag.services.recovery.recovery_session_killer import (
    RecoverySessionKiller,
)
from virgo_agentic_dag.utils.create_session_token import create_session_token

RECOVERY_AGENT_NAME = "recovery"


class RecoveryDispatchService:
    """A service for starting a recovery agent session with a batch of failed nodes."""

    def __init__(
        self,
        recovery_session_repo: RecoverySessionRepo,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        agent_launcher: AgentLauncher,
        recovery_session_killer: RecoverySessionKiller,
        dag_spec: DagSpec,
        prompt_composer: RecoveryPromptComposer,
        recovery_home: Path,
    ) -> None:
        self._recovery_session_repo = recovery_session_repo
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo

        self._agent_launcher = agent_launcher
        self._recovery_session_killer = recovery_session_killer

        self._dag_spec = dag_spec
        self._prompt_composer = prompt_composer
        self._recovery_home = recovery_home

    async def dispatch(
        self, recoverable_nodes: list[Node], current_time: datetime
    ) -> TickResponse:
        """Start a recovery session with these nodes unless the previous one is still running."""
        open_recovery_session = await self._recovery_session_repo.find_open_session()
        if open_recovery_session is not None:
            await self._end_open_session(open_recovery_session, current_time)

            return TickResponse()

        if not recoverable_nodes:
            return TickResponse()

        prompt = await self._prompt_composer.compose_prompt(recoverable_nodes)
        recovery_session = await self._launch(prompt, recoverable_nodes, current_time)
        await self._recovery_session_repo.add(recovery_session)

        for node in recoverable_nodes:
            await self._record_dispatch(node, current_time)

        return TickResponse(sessions_started=1)

    async def _end_open_session(
        self, recovery_session: RecoverySession, current_time: datetime
    ) -> None:
        is_process_alive = await recovery_session.is_process_alive()
        if not is_process_alive:
            await self._close(recovery_session, current_time)

            return

        started_at = recovery_session.started_at.replace(tzinfo=UTC)
        elapsed_seconds = (current_time - started_at).total_seconds()
        if elapsed_seconds < self._dag_spec.caps.session_timeout_seconds:
            return

        await self._recovery_session_killer.kill(recovery_session, current_time)
        await self._record_overdue(recovery_session, current_time)

    async def _record_overdue(
        self, recovery_session: RecoverySession, current_time: datetime
    ) -> None:
        node_ids = recovery_session.get_node_ids()
        nodes = await self._node_repo.get_nodes_by_ids(node_ids)
        for node in nodes:
            audit_entry = AuditEntry(
                node_id=node.id,
                state=node.state,
                note=LABELS["recoverySessionOverdue"],
                created_at=current_time,
            )

            await self._audit_entry_repo.save(audit_entry)

    async def _record_dispatch(self, node: Node, current_time: datetime) -> None:
        audit_entry = AuditEntry(
            node_id=node.id,
            state=node.state,
            note=LABELS["recoveryStarted"],
            created_at=current_time,
        )

        await self._audit_entry_repo.save(audit_entry)

    async def _close(
        self, open_recovery_session: RecoverySession, current_time: datetime
    ) -> None:
        closed_recovery_session = RecoverySession(
            id=open_recovery_session.id,
            session_token=open_recovery_session.session_token,
            pid=open_recovery_session.pid,
            started_at=open_recovery_session.started_at,
            ended_at=current_time,
            node_ids=open_recovery_session.node_ids,
        )

        await self._recovery_session_repo.close(closed_recovery_session)

    async def _launch(
        self, prompt: str, recoverable_nodes: list[Node], current_time: datetime
    ) -> RecoverySession:
        session_token = create_session_token()
        recovery_worktree = WorkTree(
            name=RECOVERY_AGENT_NAME,
            absolute_path=str(self._recovery_home),
            created_at=current_time,
        )

        executor_agent = self._dag_spec.executor_agent
        recovery_agent = NodeAgent(
            id=RECOVERY_AGENT_NAME,
            name=executor_agent.value,
            resume_token=session_token,
            node_id=RECOVERY_AGENT_NAME,
            worktree=recovery_worktree,
        )

        graph_node = GraphNode(id=RECOVERY_AGENT_NAME, executor_agent=executor_agent)
        agent_session = await self._agent_launcher.launch(
            graph_node, prompt, recovery_agent
        )

        node_ids = [node.id for node in recoverable_nodes]

        return RecoverySession(
            session_token=session_token,
            pid=agent_session.pid,
            started_at=agent_session.started_at,
            node_ids=json.dumps(node_ids),
        )

"""The SessionKiller that terminates a session's process group and closes its records."""

from __future__ import annotations

import os
import signal
from datetime import datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.infra.agent.session_killer import SessionKiller
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

ABORTED_END_STATE = "aborted"


class AgentSessionKiller(SessionKiller):
    """Terminates a session's process group and moves its node to NEEDS_HUMAN."""

    def __init__(
        self,
        agent_session_repo: AgentSessionRepo,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
    ) -> None:
        self._agent_session_repo = agent_session_repo
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo

    async def kill(self, session: AgentSession, current_time: datetime) -> None:
        """End this execution and record its ending, whether or not it was still running."""
        self._kill_processes(session)
        await self._close_session(session, current_time)
        await self._park_node(session.agent.node_id, current_time)

    def _kill_processes(self, session: AgentSession) -> None:
        if session.pid is None:
            return

        try:
            os.killpg(session.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return

    async def _close_session(
        self, session: AgentSession, current_time: datetime
    ) -> None:
        closed_session = AgentSession(
            id=session.id,
            agent_id=session.agent_id,
            started_at=session.started_at,
            ended_at=current_time,
            end_state=ABORTED_END_STATE,
            triggered_by=session.triggered_by,
            pid=session.pid,
            pid_start=session.pid_start,
        )
        await self._agent_session_repo.close(closed_session)

    async def _park_node(self, node_id: str, current_time: datetime) -> None:
        await self._node_repo.update_state(node_id, NodeState.NEEDS_HUMAN, current_time)

        audit_entry = AuditEntry(
            node_id=node_id,
            state=NodeState.NEEDS_HUMAN.value,
            note=LABELS["killedByAbort"],
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)
        emit(format_label(LABELS["agentKilled"], {"node": node_id}) + "\n")

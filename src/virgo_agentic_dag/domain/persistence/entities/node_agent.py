"""The persisted row binding a node to its agent and resume token."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase

if TYPE_CHECKING:
    from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
    from virgo_agentic_dag.domain.persistence.entities.node import Node
    from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree

TRANSCRIPT_BYTE_LIMIT = 8_000_000


class NodeAgent(EntityBase):
    __tablename__ = "node_agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    resume_token: Mapped[str] = mapped_column(String, nullable=False, default="")
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), nullable=False)

    node: Mapped[Node] = relationship(back_populates="agent")
    sessions: Mapped[list[AgentSession]] = relationship(
        back_populates="agent", order_by="AgentSession.started_at"
    )
    worktree: Mapped[WorkTree | None] = relationship(back_populates="agent")

    def get_latest_session(self) -> AgentSession | None:
        """Return the session started last, or None before the first session."""
        if not self.sessions:
            return None

        return self.sessions[-1]

    def count_overdue_sessions(self) -> int:
        """Return how many sessions of this agent ended past their deadline."""
        return sum(
            1
            for session in self.sessions
            if session.end_state == SessionStatus.OVERDUE.value
        )

    def get_transcript_lines(self, transcript_path: Path | None) -> list[str]:
        """Returns the newest complete lines from a transcript file."""
        if transcript_path is None:
            return []

        try:
            tail = self._get_tail(transcript_path)
        except FileNotFoundError:
            return []

        tail_text = tail.decode("utf-8", errors="replace")
        # TODO: page the transcript so a caller can reach lines before the limit.
        return tail_text.splitlines()

    def _get_tail(self, session_path: Path) -> bytes:
        """Return the newest bytes of the session file, cut at a line start."""
        file_size = session_path.stat().st_size
        tail_start = max(0, file_size - TRANSCRIPT_BYTE_LIMIT)
        with session_path.open("rb") as session_file:
            if tail_start == 0:
                return session_file.read()

            session_file.seek(tail_start - 1)
            tail = session_file.read()

        _, _, whole_lines = tail.partition(b"\n")

        return whole_lines

"""The persisted row for one execution of a node's agent."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase
from virgo_agentic_dag.utils.process import is_process_alive

if TYPE_CHECKING:
    from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent


class AgentSession(EntityBase):
    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("node_agents.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_state: Mapped[str] = mapped_column(String, nullable=False, default="")
    triggered_by: Mapped[str] = mapped_column(String, nullable=False, default="")
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pid_start: Mapped[str] = mapped_column(String, nullable=False, default="")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    log_tail: Mapped[str | None] = mapped_column(String, nullable=True)
    # The marks before the agent session.
    marks_before: Mapped[str | None] = mapped_column(String, nullable=True)

    agent: Mapped[NodeAgent] = relationship(back_populates="sessions")

    def has_nonzero_exit_code(self) -> bool:
        """Report whether the process exited with a code other than zero."""
        return self.exit_code is not None and self.exit_code != 0

    def get_failure_log_tail(self) -> str:
        """Return the log tail unless the exit code is zero."""
        if self.exit_code == 0:
            return ""

        return self.log_tail or ""

    def is_process_alive(self) -> bool:
        """Report whether the process recorded on this session is still running."""
        if self.pid is None:
            return False

        return is_process_alive(self.pid)

"""The persisted row for one node of a running graph."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase

if TYPE_CHECKING:
    from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
    from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent


class Node(EntityBase):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # what the node is for, as the graph file states it; name is who works on it
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recovery_attempts_allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    pull_request_settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    learnings_extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    agent: Mapped[NodeAgent | None] = relationship(back_populates="node")

    def get_agent_name(self) -> str:
        """Return the display name of this node's agent."""
        return self.name or self.title or self.id

    def get_latest_session(self) -> AgentSession | None:
        """Return the session of this node's agent started last, or None before the first."""
        if self.agent is None:
            return None

        return self.agent.get_latest_session()

    def get_pr_number(self) -> int | None:
        """Returns the pull request number from this node's agent worktree."""
        worktree = self.agent.worktree if self.agent is not None else None
        if worktree is None or not worktree.pr_number:
            return None

        return worktree.pr_number

    def is_process_dead(self) -> bool:
        """Report whether no process of this node's latest session is running."""
        latest_session = self.get_latest_session()
        if latest_session is None:
            return True

        return not latest_session.is_process_alive()

    def needs_human(self) -> bool:
        """Report whether this node is in the NEEDS_HUMAN state."""
        return self.state == NodeState.NEEDS_HUMAN.value

    def needs_human_without_agent(self) -> bool:
        """Report whether this node is in the NEEDS_HUMAN state and has no agent."""
        return self.needs_human() and self.agent is None

    def is_skippable(self) -> bool:
        """Report whether a human can skip this node in its current state."""
        state = NodeState(self.state)

        return state not in (NodeState.IN_PROGRESS, NodeState.MERGED)

    def has_failed(self) -> bool:
        """Report whether this node stopped in ERRORED or NEEDS_HUMAN, or rests on a session with a nonzero exit code."""
        state = NodeState(self.state)
        if state in (NodeState.ERRORED, NodeState.NEEDS_HUMAN):
            return True

        if state is not NodeState.RESTING:
            return False

        latest_session = self.get_latest_session()

        return latest_session is not None and latest_session.has_nonzero_exit_code()

    def can_attempt(self) -> bool:
        """Report whether this node has a recovery attempt left."""
        return self.recovery_attempts_allowed > 0

    def can_recover(self) -> bool:
        """Report whether a recovery agent may examine this node."""
        return self.is_process_dead() and self.has_failed() and self.can_attempt()

    def is_out_of_attempts(self) -> bool:
        """Report whether this node failed with no process running and no recovery attempt left."""
        return self.is_process_dead() and self.has_failed() and not self.can_attempt()

    def has_pull_request_settled(self) -> bool:
        """Report whether this node's pull request merged or closed."""
        return self.pull_request_settled_at is not None

    def is_due_for_learning_extraction(self) -> bool:
        """Report whether this node's pull request settled and its learnings are not extracted."""
        return self.has_pull_request_settled() and self.learnings_extracted_at is None

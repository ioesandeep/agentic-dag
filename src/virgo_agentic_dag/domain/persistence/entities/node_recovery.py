"""The persisted row for a single failure of a node and the recovery decision for it."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase


class NodeRecovery(EntityBase):
    __tablename__ = "node_recovery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.id"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("agent_sessions.id"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # a RecoveryCauseEnum value
    cause: Mapped[str] = mapped_column(String, nullable=False)
    recoverable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # The node recovery eligibility time.
    recover_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # The recovery action for the node failure.
    action: Mapped[str] = mapped_column(String, nullable=False, default="")

    def is_due(self, current_time: datetime) -> bool:
        """Report whether the node is recoverable and eligible for recovery at this time."""
        if not self.recoverable:
            return False

        recover_at = self.recover_at
        if recover_at.tzinfo is None:
            recover_at = recover_at.replace(tzinfo=UTC)

        return recover_at <= current_time

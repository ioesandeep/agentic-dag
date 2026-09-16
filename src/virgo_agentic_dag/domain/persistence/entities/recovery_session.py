"""The persisted row for a single execution of the recovery agent."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase
from virgo_agentic_dag.utils.process import is_process_alive


class RecoverySession(EntityBase):
    __tablename__ = "recovery_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(String, nullable=False)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # the ids of the nodes in this session's batch, as a JSON array
    node_ids: Mapped[str] = mapped_column(String, nullable=False, default="[]")

    def get_node_ids(self) -> list[str]:
        """Return the ids of the nodes in this session's batch."""
        return [str(node_id) for node_id in json.loads(self.node_ids)]

    def is_process_alive(self) -> bool:
        """Report whether the process recorded on this session is still running."""
        if self.pid is None:
            return False

        return is_process_alive(self.pid)

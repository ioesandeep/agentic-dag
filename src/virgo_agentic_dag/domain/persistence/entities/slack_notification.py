"""The persisted binding between a node and the Slack thread its updates go to."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase


class SlackNotification(EntityBase):
    __tablename__ = "slack_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    channel: Mapped[str] = mapped_column(String, nullable=False)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

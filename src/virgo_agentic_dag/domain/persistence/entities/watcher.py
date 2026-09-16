"""The record of a run's watcher process, kept so start and abort can find it later."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase


class Watcher(EntityBase):
    __tablename__ = "watchers"

    dag_name: Mapped[str] = mapped_column(String, primary_key=True)
    # its own process group leader, so one killpg ends everything it started
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

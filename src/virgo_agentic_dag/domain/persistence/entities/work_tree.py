"""The working copy one agent builds in, kept as record after the disk is reclaimed."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase

if TYPE_CHECKING:
    from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent

LOG_TAIL_LINE_COUNT = 40


class WorkTree(EntityBase):
    __tablename__ = "work_trees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("node_agents.id"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    absolute_path: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False, default="")
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # The pull request head SHA at the start of a worktree session.
    head_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    marks: Mapped[str] = mapped_column(String, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reclaimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    agent: Mapped[NodeAgent] = relationship(back_populates="worktree")

    def exists_on_disk(self) -> bool:
        """Report whether this worktree's directory is present on this host."""
        return Path(self.absolute_path).is_dir()

    def is_reclaimed(self) -> bool:
        """Report whether this worktree's disk copy was removed and the row kept as history."""
        return self.reclaimed_at is not None

    def get_log_path(self) -> Path:
        """Return the path of the session log written beside this worktree."""
        return Path(self.absolute_path).with_suffix(".log")

    def get_exit_path(self) -> Path:
        """Return the path of the exit code file written beside this worktree."""
        return Path(self.absolute_path).with_suffix(".exit")

    def find_exit_code(self) -> int | None:
        """Returns the work tree's recorded exit code."""
        try:
            exit_text = self.get_exit_path().read_text()
        except FileNotFoundError:
            return None

        exit_code = exit_text.strip()
        if not exit_code.isdigit():
            return None

        return int(exit_code)

    def find_log_tail(self) -> str | None:
        """Return the last lines of the session log, or None where there is no log."""
        try:
            log_text = self.get_log_path().read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return None

        log_lines = log_text.splitlines()

        return "\n".join(log_lines[-LOG_TAIL_LINE_COUNT:])

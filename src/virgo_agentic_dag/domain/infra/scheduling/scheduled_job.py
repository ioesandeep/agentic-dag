"""The host job that advances a run, recorded so a later command can retire it."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from virgo_agentic_dag.domain.persistence.entities.entity_base import EntityBase

LABEL_PREFIX = "fyi.virgo.dag"


class ScheduledJob(EntityBase):
    __tablename__ = "scheduled_jobs"

    dag_name: Mapped[str] = mapped_column(String, primary_key=True)
    # what the host calls this job
    label: Mapped[str] = mapped_column(String, nullable=False)
    # the command line to run, as a JSON array
    argv: Mapped[str] = mapped_column(String, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    working_directory: Mapped[str] = mapped_column(String, nullable=False)
    log_path: Mapped[str] = mapped_column(String, nullable=False)
    # what the host must put in the environment, as a JSON object, since it reads no profile
    environment: Mapped[str] = mapped_column(String, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @classmethod
    def get_label(cls, dag_name: str) -> str:
        """Return the label a host knows this dag's own job by."""
        return f"{LABEL_PREFIX}.{dag_name}"

    def get_argv(self) -> list[str]:
        """Return the command line this job runs."""
        return [str(word) for word in json.loads(self.argv)]

    def get_dag_path(self) -> Path | None:
        """Return the dag file named in this job's command line, or None when absent."""
        argv = self.get_argv()
        if "--dag" not in argv:
            return None

        position = argv.index("--dag") + 1
        if position >= len(argv):
            return None

        return Path(argv[position])

    def get_environment(self) -> Mapping[str, str]:
        """Return what this job needs in its environment."""
        return {
            str(key): str(value) for key, value in json.loads(self.environment).items()
        }

    def get_working_directory(self) -> Path:
        """Return the directory this job runs in."""
        return Path(self.working_directory)

    def get_log_path(self) -> Path:
        """Return the file this job's output is appended to."""
        return Path(self.log_path)

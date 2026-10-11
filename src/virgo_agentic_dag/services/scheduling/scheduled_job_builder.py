"""Describing the job a host must run to keep one dag advancing until it settles."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from virgo_agentic_dag.domain.command.start_command import StartCommand
from virgo_agentic_dag.domain.infra.scheduling.host_platform import HostPlatform
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec

LOG_FILE_NAME = "start.log"


class ScheduledJobBuilder:
    """Turns what `start` was pointed at into the job a host can run unattended."""

    def __init__(self, dag_spec: DagSpec, executable: Path) -> None:
        self._dag_spec = dag_spec
        self._executable = executable

    def get_dag_name(self) -> str:
        """Return the dag this builder describes jobs for."""
        return self._dag_spec.name

    def build(self, command: StartCommand, current_time: datetime) -> ScheduledJob:
        """Return the job that runs this dag's next pass, and every pass after it."""
        home = command.dag_path.parent.resolve()
        environment_json = self._get_environment_json()

        return ScheduledJob(
            dag_name=self._dag_spec.name,
            label=ScheduledJob.get_label(self._dag_spec.name),
            argv=json.dumps(self._build_argv(command)),
            interval_seconds=self._dag_spec.tick_interval_seconds,
            working_directory=str(home),
            log_path=str(home / LOG_FILE_NAME),
            environment=environment_json,
            created_at=current_time,
        )

    def _build_argv(self, command: StartCommand) -> list[str]:
        return [
            str(self._executable),
            "start",
            "--dag",
            str(command.dag_path.resolve()),
        ]

    def _get_environment_json(self) -> str:
        environment = {"PATH": os.environ.get("PATH", "")}
        host_platform = HostPlatform.current()
        if host_platform is HostPlatform.LINUX:
            home = Path.home()
            config_home = os.getenv("XDG_CONFIG_HOME", "")
            config_path = Path(config_home)
            is_absolute = config_path.is_absolute()
            if not is_absolute:
                config_path = home / ".config"

            home_text = str(home)
            config_home_text = str(config_path)
            environment.update(HOME=home_text, XDG_CONFIG_HOME=config_home_text)

        return json.dumps(environment)

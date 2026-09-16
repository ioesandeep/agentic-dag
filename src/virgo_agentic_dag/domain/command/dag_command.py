"""The base for commands that read a graph file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from virgo_agentic_dag.domain.command.command import Command


@dataclass(frozen=True)
class DagCommand(Command):
    """A command that points at the dag file describing the run."""

    dag_path: Path

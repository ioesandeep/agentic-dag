"""The parsed tick request, naming the graph file to advance by one pass."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class TickCommand(DagCommand):
    """A request to advance the run by one control pass."""

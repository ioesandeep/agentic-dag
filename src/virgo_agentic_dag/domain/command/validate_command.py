"""The parsed validate request, naming the graph file to check."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class ValidateCommand(DagCommand):
    """A request to check that one graph file is a legal dag."""

    def requires_run_lock(self) -> bool:
        """Validation only reads the graph, so it runs without the run lock."""
        return False

    def requires_database(self) -> bool:
        """Validation only reads the graph, so it opens no database."""
        return False

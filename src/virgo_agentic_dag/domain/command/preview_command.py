"""The parsed preview request, naming the graph file to render."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class PreviewCommand(DagCommand):
    """A request to see one graph as a diagram before a run spends anything."""

    def requires_run_lock(self) -> bool:
        """Preview only reads the graph, so it runs without the run lock."""
        return False

    def requires_database(self) -> bool:
        """Preview only reads the graph, so it opens no database."""
        return False

"""The examine command, naming the node whose current row to print."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class ExamineCommand(DagCommand):
    """A command to examine the node identified by `node_id`."""

    node_id: str

    def requires_run_lock(self) -> bool:
        """An examine read changes nothing, so it needs no run lock."""
        return False

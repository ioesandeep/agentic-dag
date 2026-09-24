"""The command for stopping a node's running session."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class StopCommand(DagCommand):
    """A command for stopping a node's running session."""

    node_id: str

    def requires_run_lock(self) -> bool:
        """Defer run lock acquisition to the stop handler because it waits for the running pass instead of failing."""
        return False

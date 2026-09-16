"""The skip command, naming the node to skip."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class SkipCommand(DagCommand):
    """A node a human skips, so its dependents stop waiting on it."""

    node_id: str

    def requires_run_lock(self) -> bool:
        """Skip claims the run itself, waiting out the pass that has it instead of failing."""
        return False

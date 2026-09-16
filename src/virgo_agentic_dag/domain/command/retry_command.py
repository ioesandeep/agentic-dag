"""The retry command, naming the stopped node to put back in the run."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.dag_command import DagCommand


@dataclass(frozen=True)
class RetryCommand(DagCommand):
    """A node a human takes out of ERRORED or NEEDS_HUMAN and puts back in the run."""

    node_id: str
    # when true, the next start opens a new conversation instead of resuming the recorded one
    reset: bool = False

    def requires_run_lock(self) -> bool:
        """Retry claims the run itself, waiting out the pass that holds it instead of failing."""
        return False

"""The parsed abort request, which identifies its run by dag name alone."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.command import Command


@dataclass(frozen=True)
class AbortCommand(Command):
    """A run to stop, named rather than described, so a broken graph cannot block it."""

    # TODO: take the dag path like DagCommand and derive the name from the spec

    def requires_run_lock(self) -> bool:
        """Ending a run must never be blocked by the very pass it is ending."""
        return False

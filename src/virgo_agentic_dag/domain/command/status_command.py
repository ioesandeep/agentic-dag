"""The status command, holding the name of the run to report on."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.command import Command


@dataclass(frozen=True)
class StatusCommand(Command):
    """A request to print the named run's recorded state."""

    def requires_run_lock(self) -> bool:
        """A status read changes nothing, so it needs no run lock."""
        return False

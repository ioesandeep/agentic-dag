"""The log command, holding the name of the run whose history to print."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.command import Command


@dataclass(frozen=True)
class LogCommand(Command):
    """A request to print the named run's audit trail."""

    def requires_run_lock(self) -> bool:
        """A history read changes nothing, so it needs no run lock."""
        return False

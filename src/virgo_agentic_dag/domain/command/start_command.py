"""The parsed start request, which runs one pass and schedules the rest."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.tick_command import TickCommand


@dataclass(frozen=True)
class StartCommand(TickCommand):
    """A pass that also registers the host job re-running `start` until the run completes."""

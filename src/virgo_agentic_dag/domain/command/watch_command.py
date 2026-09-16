"""The watch command, holding a dag name and an optional stream url."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.command import Command


@dataclass(frozen=True)
class WatchCommand(Command):
    """A run whose pull request events should trigger passes until it completes."""

    # TODO: take the dag path like DagCommand and derive the name from the spec

    # overrides the sse_url from the dag file when set
    sse_url: str = ""

    def requires_run_lock(self) -> bool:
        """Watching only triggers passes, so it runs without the run lock."""
        return False

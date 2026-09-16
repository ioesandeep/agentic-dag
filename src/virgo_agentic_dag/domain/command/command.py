"""The base every parsed command extends, so handlers share one family."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Command:
    """The parsed form of one dagctl invocation, carrying data only."""

    # names the dag when the command carries no graph to read it from
    dag_name: str = ""

    def requires_run_lock(self) -> bool:
        """Commands take the run lock unless a subclass opts out."""
        return True

    def requires_database(self) -> bool:
        """Commands open the run's database unless a subclass opts out."""
        return True

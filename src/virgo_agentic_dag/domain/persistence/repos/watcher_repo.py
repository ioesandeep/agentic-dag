"""Where a run's watcher record lives, whatever database holds it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher


class WatcherRepo(ABC):
    """Keeps at most one watcher row per run, one explicit write each."""

    @abstractmethod
    async def save(self, watcher: Watcher) -> None:
        """Record this run's watcher, replacing any earlier record."""

    @abstractmethod
    async def get_by_dag_name(self, dag_name: str) -> Watcher | None:
        """Return the watcher recorded for this dag, or None when none was."""

    @abstractmethod
    async def delete(self, watcher: Watcher) -> None:
        """Delete this watcher's row."""

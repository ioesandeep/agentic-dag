"""Where each agent's worktree record lives, kept after the disk copy is reclaimed."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree


class WorkTreeRepo(ABC):
    """Persistence operations for work tree state."""

    @abstractmethod
    async def record_publication(self, worktree: WorkTree) -> None:
        """Record a worktree's branch, pull request number, and head SHA."""

    @abstractmethod
    async def save(self, worktree: WorkTree) -> None:
        """Persists a work tree's state."""

    @abstractmethod
    async def advance_marks(self, worktree: WorkTree) -> None:
        """Record the signal watermarks this worktree row carries."""

    @abstractmethod
    async def mark_reclaimed(self, worktree: WorkTree) -> None:
        """Record that this worktree's disk copy is gone, keeping the row as history."""

    @abstractmethod
    async def get_published(self) -> list[WorkTree]:
        """Return every worktree that has a pull request and is not reclaimed."""

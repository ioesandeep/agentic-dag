"""WorkTreeRepo on SQLite, one row per agent worktree."""

from __future__ import annotations

from sqlalchemy import select, update
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase


class SqliteWorkTreeRepo(WorkTreeRepo):
    """Writes worktree rows through sessions the database hands out."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def record_publication(self, worktree: WorkTree) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(WorkTree)
                .where(WorkTree.id == worktree.id)
                .values(
                    branch=worktree.branch,
                    pr_number=worktree.pr_number,
                    head_sha=worktree.head_sha,
                )
            )
            await session.execute(statement)
            await session.commit()

    async def save(self, worktree: WorkTree) -> None:
        async with self._database.open_session() as session:
            await session.merge(worktree)
            await session.commit()

    async def advance_marks(self, worktree: WorkTree) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(WorkTree)
                .where(WorkTree.id == worktree.id)
                .values(marks=worktree.marks)
            )
            await session.execute(statement)
            await session.commit()

    async def mark_reclaimed(self, worktree: WorkTree) -> None:
        async with self._database.open_session() as session:
            statement = (
                update(WorkTree)
                .where(WorkTree.id == worktree.id)
                .values(reclaimed_at=worktree.reclaimed_at)
            )
            await session.execute(statement)
            await session.commit()

    async def get_published(self) -> list[WorkTree]:
        async with self._database.open_session() as session:
            statement = select(WorkTree).where(
                WorkTree.pr_number > 0, WorkTree.reclaimed_at.is_(None)
            )
            result = await session.execute(statement)

            return list(result.scalars())

"""The dependency-injection container a command resolves its collaborators from."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TextIO, cast

from sqlalchemy.ext.asyncio import AsyncSession
from virgo_agentic_dag.domain.command.command import Command
from virgo_agentic_dag.utils.dag_utils import get_dag_db_path
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

_application_context: ContextVar[ApplicationContext | None] = ContextVar(
    "application_context", default=None
)


class ApplicationContext:
    """Carries what the running command needs from its surroundings and builds every
    collaborator exactly once, the first time it is asked for."""

    def __init__(self, command: Command, output_writer: TextIO) -> None:
        self._command = command
        self._output_writer = output_writer
        self._repo_slug = ""
        self._factories: dict[type, Callable[[ApplicationContext], object]] = {}
        self._beans: dict[type, object] = {}

    @property
    def command(self) -> Command:
        return self._command

    @property
    def output_writer(self) -> TextIO:
        return self._output_writer

    @property
    def repo_slug(self) -> str:
        return self._repo_slug

    def set_repo_slug(self, repo_slug: str) -> None:
        """Set the repository slug for the run's pull request links."""
        self._repo_slug = repo_slug

    def emit(self, text: str) -> None:
        """Write the command's output, flushing so a long pass is not left buffered."""
        self._output_writer.write(text)
        self._output_writer.flush()

    def register[BeanT](
        self, kind: type[BeanT], factory: Callable[[ApplicationContext], BeanT]
    ) -> None:
        """Declare how to build this kind of collaborator when it is first asked for."""
        self._factories[kind] = factory

    def get[BeanT](self, kind: type[BeanT]) -> BeanT:
        """Return the one instance of this kind, building it on the first ask."""
        if kind not in self._beans:
            factory = self._factories.get(kind)
            if factory is None:
                raise LookupError(f"no factory registered for {kind.__name__}")

            self._beans[kind] = factory(self)

        return cast(BeanT, self._beans[kind])

    def get_dag_name(self) -> str:
        """Return the dag this command is about, from the command or from its graph."""
        return self._command.dag_name or self.get(DagSpec).name

    def get_db_path(self) -> Path:
        """Return where this run's database lives, from its graph or its name alone."""
        if self._command.dag_name:
            return get_dag_db_path(self._command.dag_name)

        return self.get(DagSpec).get_db_path()

    def open_session(self) -> AsyncSession:
        """Return a database session for one unit of work, wherever it is asked from."""
        return self.get(SqliteDatabase).open_session()


def get_context() -> ApplicationContext:
    """Return the context the running command was booted with, wherever it is asked from."""
    context = _application_context.get()
    if context is None:
        raise LookupError("no application context is active")

    return context


def emit(text: str) -> None:
    """Write to the bound context's output without threading a writer through callers."""
    get_context().emit(text)


def bind_context(context: ApplicationContext) -> Token[ApplicationContext | None]:
    """Make this the context every ambient lookup resolves to, from here on."""
    return _application_context.set(context)


def unbind_context(token: Token[ApplicationContext | None]) -> None:
    """Put back whatever context was bound before, so nothing outlives its command."""
    _application_context.reset(token)

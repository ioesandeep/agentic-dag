"""Builds and tears down the application context around a command's execution."""

# mypy: disable-error-code="type-abstract"

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import Token
from typing import TextIO

from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.bootstrap.register_beans import register_beans
from virgo_agentic_dag.domain.command.command import Command
from virgo_agentic_dag.domain.command.dag_command import DagCommand
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase

logger = logging.getLogger(__name__)


@asynccontextmanager
async def initialize_context(
    command: Command, output_writer: TextIO
) -> AsyncGenerator[ApplicationContext]:
    """Yield a fully wired application context and release it on exit."""
    context = ApplicationContext(command, output_writer)
    register_beans(context)
    context.set_repo_slug(await _get_repo_slug(context))
    run_lock = _acquire_run_lock(context)
    token: Token[ApplicationContext | None] | None = None
    database: SqliteDatabase | None = None

    try:
        token = bind_context(context)

        if command.requires_database():
            database = context.get(SqliteDatabase)
            await database.upgrade_to_head()

        yield context
    finally:
        await context.get(NotificationPublisher).drain()

        if database is not None:
            await database.dispose()

        if token is not None:
            unbind_context(token)

        if run_lock is not None:
            run_lock.release()


def _acquire_run_lock(context: ApplicationContext) -> RunLock | None:
    """Claim the run before anything opens, when this command must be its only pass."""
    if not context.command.requires_run_lock():
        return None

    run_lock = context.get(RunLock)
    run_lock.acquire()

    return run_lock


async def _get_repo_slug(context: ApplicationContext) -> str:
    """Return the repository slug for the run's pull request links."""
    command = context.command
    if not isinstance(command, DagCommand) or not command.requires_database():
        return ""

    dag_spec = context.get(DagSpec)
    if dag_spec.repo_slug:
        return dag_spec.repo_slug

    if dag_spec.project_root is None:
        return ""

    try:
        return await context.get(CodeRepo).get_repo_slug(dag_spec.project_root)
    except (ObservationError, OSError) as error:
        logger.warning("the repository of %s did not resolve: %s", dag_spec.name, error)

        return ""

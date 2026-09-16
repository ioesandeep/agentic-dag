"""Runs the `serve` command."""

from __future__ import annotations

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.serve_command import ServeCommand
from virgo_agentic_dag.domain.infra.web.web_server import WebServer
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)


class ServeCommandHandler(CommandHandler[ServeCommand]):
    """Serves the read-only web api."""

    def __init__(
        self, web_server: WebServer, database_registry: DagDatabaseRegistry
    ) -> None:
        self._web_server = web_server
        self._database_registry = database_registry

    async def handle(self, command: ServeCommand) -> ExitCode:
        try:
            await self._web_server.serve(command.host, command.port)
        finally:
            await self._database_registry.dispose()

        return ExitCode.SUCCESS

"""Validates a graph file and reports whether the controller can execute it."""

from __future__ import annotations

from typing import TextIO

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.validate_command import ValidateCommand
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.graph_validation_service import (
    GraphValidationService,
)
from virgo_agentic_dag.labels.en import LABELS


class ValidateCommandHandler(CommandHandler[ValidateCommand]):
    """Validates the graph named by the command and writes each finding on its own line."""

    def __init__(
        self,
        graph_builder: GraphBuilder,
        validation_service: GraphValidationService,
        out: TextIO,
    ) -> None:
        self._graph_builder = graph_builder
        self._validation_service = validation_service
        self._out = out

    async def handle(self, command: ValidateCommand) -> ExitCode:
        graph = self._graph_builder.build_from_path(command.dag_path)
        result = self._validation_service.validate_graph(graph)

        self._out.write(result.describe())
        if result.is_blocking():
            return ExitCode.FAILURE

        self._out.write(LABELS["graphValid"])

        return ExitCode.SUCCESS

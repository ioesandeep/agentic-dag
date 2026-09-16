"""Runs the `examine` command through the node examination service."""

from __future__ import annotations

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.examine_command import ExamineCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.services.recovery.node_examination_service import (
    NodeExaminationService,
)


class ExamineCommandHandler(CommandHandler[ExamineCommand]):
    """Hands the examine command to the service that prints the node's row."""

    def __init__(self, node_examination_service: NodeExaminationService) -> None:
        self._node_examination_service = node_examination_service

    async def handle(self, command: ExamineCommand) -> ExitCode:
        return await self._node_examination_service.examine(command)

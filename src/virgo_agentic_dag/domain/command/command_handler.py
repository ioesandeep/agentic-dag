"""The handler interface that executes one parsed command."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.command.command import Command
from virgo_agentic_dag.domain.command.exit_code import ExitCode


class CommandHandler[CommandT: Command](ABC):
    """Carries out one command from parsed data to exit code."""

    @abstractmethod
    async def handle(self, command: CommandT) -> ExitCode:
        """Execute the command and return its exit code."""

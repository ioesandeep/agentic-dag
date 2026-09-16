"""Holds the run lock while the adopt service writes the adopted node."""

from __future__ import annotations

import asyncio

from virgo_agentic_dag.domain.command.adopt_command import AdoptCommand
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.services.run.adopt_service import AdoptService


class AdoptCommandHandler(CommandHandler[AdoptCommand]):
    """Claims the run for the adoption's writes and frees it however they end."""

    def __init__(self, run_lock: RunLock, adopt_service: AdoptService) -> None:
        self._run_lock = run_lock
        self._adopt_service = adopt_service

    async def handle(self, command: AdoptCommand) -> ExitCode:
        await asyncio.to_thread(self._run_lock.acquire_waiting)

        try:
            return await self._adopt_service.adopt(command)
        finally:
            self._run_lock.release()

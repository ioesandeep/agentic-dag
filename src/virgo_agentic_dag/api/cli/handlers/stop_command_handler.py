"""Runs the `stop` command."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.stop_command import StopCommand
from virgo_agentic_dag.domain.exceptions.run.stop_refused import StopRefused
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.stop.node_stop_service import NodeStopService
from virgo_agentic_dag.utils.format_label import format_label


class StopCommandHandler(CommandHandler[StopCommand]):
    """A stop handler that claims the run and prints the stopped node or the stop failure."""

    def __init__(self, run_lock: RunLock, node_stop_service: NodeStopService) -> None:
        self._run_lock = run_lock
        self._node_stop_service = node_stop_service

    async def handle(self, command: StopCommand) -> ExitCode:
        await asyncio.to_thread(self._run_lock.acquire_waiting)

        try:
            current_time = datetime.now(UTC)
            await self._node_stop_service.stop(command, current_time)
            emit(format_label(LABELS["nodeStopped"], {"node_id": command.node_id}))

            return ExitCode.SUCCESS
        except StopRefused as refused:
            emit(str(refused))

            return ExitCode.FAILURE
        finally:
            self._run_lock.release()

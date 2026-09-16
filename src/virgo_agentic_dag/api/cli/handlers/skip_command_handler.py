"""Runs the `skip` command, printing the node it skipped and each one it returned to pending."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.run.node_skip_service import NodeSkipService
from virgo_agentic_dag.utils.format_label import format_label


class SkipCommandHandler(CommandHandler[SkipCommand]):
    """Claims the run for the skip's writes and prints every node it moved."""

    def __init__(self, run_lock: RunLock, node_skip_service: NodeSkipService) -> None:
        self._run_lock = run_lock
        self._node_skip_service = node_skip_service

    async def handle(self, command: SkipCommand) -> ExitCode:
        await asyncio.to_thread(self._run_lock.acquire_waiting)

        try:
            current_time = datetime.now(UTC)
            pending_node_ids = await self._node_skip_service.skip(command, current_time)
            self._report(command.node_id, pending_node_ids)

            return ExitCode.SUCCESS
        except SkipRefused as refused:
            emit(str(refused))

            return ExitCode.FAILURE
        finally:
            self._run_lock.release()

    def _report(self, node_id: str, pending_node_ids: list[str]) -> None:
        """Print the skipped node and each node returned to pending."""
        emit(format_label(LABELS["nodeSkipped"], {"node_id": node_id}))

        for pending_node_id in pending_node_ids:
            emit(format_label(LABELS["nodePendingAgain"], {"node_id": pending_node_id}))

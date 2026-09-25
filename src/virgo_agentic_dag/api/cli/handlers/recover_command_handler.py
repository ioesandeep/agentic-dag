"""Claims the run lock while the recovery service acts on a node and records the verdict."""

from __future__ import annotations

import asyncio

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.recover_command import RecoverCommand
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.locking.run_lock_config import RunLockConfig
from virgo_agentic_dag.services.recovery.node_recovery_service import (
    NodeRecoveryService,
)


class RecoverCommandHandler(CommandHandler[RecoverCommand]):
    """Claims the run for the recovery's writes and frees it however they end."""

    def __init__(
        self, run_lock: RunLock, node_recovery_service: NodeRecoveryService
    ) -> None:
        self._run_lock = run_lock
        self._node_recovery_service = node_recovery_service

    async def handle(self, command: RecoverCommand) -> ExitCode:
        run_lock_config = RunLockConfig(timeout=command.timeout)
        await asyncio.to_thread(self._run_lock.acquire_lock, run_lock_config)

        try:
            return await self._node_recovery_service.recover(command)
        finally:
            self._run_lock.release()

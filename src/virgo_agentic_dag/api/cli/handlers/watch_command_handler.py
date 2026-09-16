"""Runs the `watch` command until the run completes."""

from __future__ import annotations

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.services.watching.run_watcher import RunWatcher


class WatchCommandHandler(CommandHandler[WatchCommand]):
    """Runs the watcher until the run completes or the process is killed."""

    def __init__(self, run_watcher: RunWatcher) -> None:
        self._run_watcher = run_watcher

    async def handle(self, command: WatchCommand) -> ExitCode:
        return await self._run_watcher.watch(command)

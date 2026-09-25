"""The recover command, naming the node and everything the recovery agent decided about it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from virgo_agentic_dag.domain.command.dag_command import DagCommand
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum


@dataclass(frozen=True)
class RecoverCommand(DagCommand):
    """A request to act on one failed node and record the failure and the verdict."""

    node_id: str
    cause: RecoveryCauseEnum
    action: str
    recoverable: bool = True
    # The time when the node becomes eligible for recovery again, with the write time as the default.
    recover_at: datetime | None = None
    # whether to put the worktree's watermarks back to before the latest session
    restore_marks: bool = False
    # the turn to resume the node's conversation with, empty when the node stays stopped
    wake_message: str = ""
    # the maximum run lock wait in seconds, or None for an unlimited wait
    timeout: float | None = None

    def requires_run_lock(self) -> bool:
        """Recover claims the run itself, waiting out the pass that has it instead of failing."""
        return False

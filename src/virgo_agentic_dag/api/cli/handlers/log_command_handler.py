"""Runs the `log` command, printing what the run's audit trail records."""

from __future__ import annotations

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.log_command import LogCommand
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class LogCommandHandler(CommandHandler[LogCommand]):
    """Reports every transition a run has recorded, in the order they were written."""

    def __init__(self, audit_entry_repo: AuditEntryRepo) -> None:
        self._audit_entry_repo = audit_entry_repo

    async def handle(self, command: LogCommand) -> ExitCode:
        entries = await self._audit_entry_repo.get_all()

        if not entries:
            emit(format_label(LABELS["logEmpty"], {"dag": command.dag_name}))

            return ExitCode.SUCCESS

        self._report_entries(entries)

        return ExitCode.SUCCESS

    def _report_entries(self, entries: list[AuditEntry]) -> None:
        for entry in entries:
            args = {"node_id": entry.node_id, "state": entry.state, "note": entry.note}
            emit(format_label(LABELS["logEntry"], args))

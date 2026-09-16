import io
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.dagctl import main
from virgo_agentic_dag.api.cli.handlers.log_command_handler import LogCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.log_command import LogCommand
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 4, tzinfo=UTC)


@pytest.fixture
def build_entry() -> Callable[[str, str, str], AuditEntry]:
    return lambda node_id, state, note: AuditEntry(
        node_id=node_id, state=state, note=note, created_at=NOW
    )


async def test_prints_every_entry_in_the_order_it_was_written(
    mocker: MockerFixture, build_entry: Callable[[str, str, str], AuditEntry]
) -> None:
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [
        build_entry("A", "in_progress", "claude started work"),
        build_entry("B", "in_progress", "claude started work"),
        build_entry("A", "resting", "opened #7"),
    ]

    handler = LogCommandHandler(audit_entry_repo=audit_entry_repo)

    out = io.StringIO()
    command = LogCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == (
        "A\tin_progress\tclaude started work\n"
        "B\tin_progress\tclaude started work\n"
        "A\tresting\topened #7\n"
    )


async def test_says_there_is_no_history_when_the_trail_is_empty(
    mocker: MockerFixture,
) -> None:
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = []

    handler = LogCommandHandler(audit_entry_repo=audit_entry_repo)

    out = io.StringIO()
    command = LogCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == "demo has no history yet\n"


def test_refuses_when_no_run_lives_under_the_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    exit_code = main(["log", "ghost"])

    assert exit_code == 1
    assert "no dag named ghost lives on this host" in capsys.readouterr().err
    assert not (tmp_path / "ghost").exists()

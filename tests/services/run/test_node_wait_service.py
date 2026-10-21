from datetime import UTC, datetime, timedelta

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.run.node_wait_service import NodeWaitService

pytestmark = pytest.mark.unit


async def test_wait_records_the_resume_time_and_audit_note_when_the_node_receives_a_wait(
    mocker: MockerFixture,
) -> None:
    current_time = datetime(2026, 10, 19, tzinfo=UTC)
    resume_at = current_time + timedelta(hours=2)
    note = "Usage limit resets at the resume time."

    node_repo = mocker.MagicMock(spec=NodeRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    service = NodeWaitService(node_repo=node_repo, audit_entry_repo=audit_entry_repo)

    await service.wait("A", resume_at, note, current_time)

    node_repo.update_state.assert_awaited_once_with(
        "A", NodeState.PENDING, current_time, resume_at=resume_at
    )

    audit_entry_repo.save.assert_awaited_once()

    audit_entry = audit_entry_repo.save.await_args.args[0]

    assert audit_entry.node_id == "A"
    assert audit_entry.state == NodeState.PENDING.value
    assert audit_entry.note == note
    assert audit_entry.created_at == current_time

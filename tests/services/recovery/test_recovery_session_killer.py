from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (
    SqliteDatabase,  # noqa: F401
)
from virgo_agentic_dag.services.recovery.recovery_session_killer import (
    RecoverySessionKiller,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("pid", "is_process_alive"), [(4242, True), (4242, False), (None, False)]
)
async def test_kill_closes_the_recovery_session_when_the_process_is_alive_or_exited(
    mocker: MockerFixture, pid: int | None, is_process_alive: bool
) -> None:
    mocker.patch("os.waitpid", side_effect=ChildProcessError)
    mocker.patch(
        "os.kill", side_effect=None if is_process_alive else ProcessLookupError
    )

    started_at = datetime(2026, 8, 2, tzinfo=UTC)
    recovery_session = RecoverySession(
        id=1,
        session_token="token-1",
        pid=pid,
        started_at=started_at,
        node_ids='["A"]',
    )

    current_time = datetime(2026, 8, 3, tzinfo=UTC)

    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    process_killer = mocker.MagicMock(spec=ProcessKiller)
    recovery_session_killer = RecoverySessionKiller(
        recovery_session_repo=recovery_session_repo, process_killer=process_killer
    )

    await recovery_session_killer.kill(recovery_session, current_time)

    recovery_session_repo.close.assert_awaited_once()

    closed_recovery_session = recovery_session_repo.close.await_args.args[0]

    assert closed_recovery_session.id == recovery_session.id
    assert closed_recovery_session.ended_at == current_time
    assert recovery_session.ended_at is None

    if is_process_alive:
        process_killer.kill.assert_called_once_with(pid)
    else:
        process_killer.kill.assert_not_called()

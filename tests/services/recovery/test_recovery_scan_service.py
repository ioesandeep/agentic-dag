import json
import os
import subprocess
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_recovery_session_repo import (
    SqliteRecoverySessionRepo,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.recovery.recovery_scan_service import (
    RecoveryScanService,
)
from virgo_agentic_dag.utils.format_label import format_label

pytestmark = pytest.mark.integration

BuildNode = Callable[[NodeState, int | None, int, int], Node]
BuildNodeRecovery = Callable[[bool, timedelta], NodeRecovery]
NodeRecoverySpec = tuple[bool, timedelta]


@pytest.fixture
def current_time() -> datetime:
    return datetime(2026, 9, 4, tzinfo=UTC)


@pytest.fixture
def dead_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()

    return process.pid


@pytest.fixture
async def database(tmp_path: Path) -> AsyncGenerator[SqliteDatabase]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield database

    await database.dispose()


@pytest.fixture
def build_node(current_time: datetime) -> BuildNode:
    return lambda state, exit_code, pid, recovery_attempts_allowed: Node(
        id="A",
        state=state.value,
        created_at=current_time,
        updated_at=current_time,
        recovery_attempts_allowed=recovery_attempts_allowed,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            node_id="A",
            sessions=[
                AgentSession(
                    agent_id="agent-A",
                    started_at=current_time,
                    ended_at=current_time,
                    pid=pid,
                    exit_code=exit_code,
                )
            ],
        ),
    )


@pytest.fixture
def build_node_recovery(current_time: datetime) -> BuildNodeRecovery:
    return lambda recoverable, delay: NodeRecovery(
        node_id="A",
        session_id=1,
        detected_at=current_time,
        cause=RecoveryCauseEnum.PROVIDER_FAILURE.value,
        recoverable=recoverable,
        recover_at=current_time + delay,
        action="",
    )


@pytest.mark.parametrize(
    ("state", "exit_code", "end_state"),
    [
        (NodeState.ERRORED, None, SessionStatus.FINISHED.value),
        (NodeState.NEEDS_HUMAN, 0, SessionStatus.FINISHED.value),
        (NodeState.RESTING, 1, SessionStatus.FINISHED.value),
        (NodeState.RESTING, None, SessionStatus.OVERDUE.value),
    ],
    ids=[
        "errored",
        "needs-human",
        "resting-with-a-nonzero-exit-code",
        "resting-with-an-overdue-session",
    ],
)
async def test_get_recoverable_nodes_returns_the_node_when_its_process_is_dead_and_an_attempt_is_left(
    state: NodeState,
    exit_code: int | None,
    end_state: str,
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    current_time: datetime,
) -> None:
    node = build_node(state, exit_code, dead_pid, 1)
    latest_session = node.get_latest_session()
    assert latest_session is not None
    latest_session.end_state = end_state

    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=SqliteNodeRepo(database),
        node_recovery_repo=SqliteNodeRecoveryRepo(database),
        audit_entry_repo=SqliteAuditEntryRepo(database),
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    recoverable_nodes = await service.get_recoverable_nodes(current_time)

    assert [recoverable.id for recoverable in recoverable_nodes] == ["A"]


@pytest.mark.parametrize(
    ("state", "exit_code", "is_process_alive", "node_recovery_specs", "has_agent"),
    [
        (NodeState.RESTING, 0, False, [], True),
        (NodeState.ERRORED, 1, True, [], True),
        (NodeState.ERRORED, 1, False, [(True, timedelta(hours=1))], True),
        (NodeState.NEEDS_HUMAN, 0, False, [(False, timedelta())], True),
        (NodeState.NEEDS_HUMAN, None, False, [], False),
    ],
    ids=[
        "resting-with-a-zero-exit-code",
        "process-alive",
        "held-by-a-later-recover-at",
        "marked-unrecoverable",
        "needs-human-without-an-agent",
    ],
)
async def test_get_recoverable_nodes_returns_nothing_when_the_node_is_not_due(
    state: NodeState,
    exit_code: int | None,
    is_process_alive: bool,
    node_recovery_specs: list[NodeRecoverySpec],
    has_agent: bool,
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    build_node_recovery: BuildNodeRecovery,
    current_time: datetime,
) -> None:
    pid = os.getpid() if is_process_alive else dead_pid
    node = build_node(state, exit_code, pid, 3)
    if not has_agent:
        node.agent = None

    node_recoveries = [
        build_node_recovery(recoverable, delay)
        for recoverable, delay in node_recovery_specs
    ]

    async with database.open_session() as db_session:
        db_session.add_all([node, *node_recoveries])
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=node_repo,
        node_recovery_repo=SqliteNodeRecoveryRepo(database),
        audit_entry_repo=SqliteAuditEntryRepo(database),
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    recoverable_nodes = await service.get_recoverable_nodes(current_time)

    assert recoverable_nodes == []
    stored_node = await node_repo.read("A")
    assert stored_node is not None
    assert stored_node.recovery_attempts_allowed == 3


async def test_get_recoverable_nodes_moves_the_node_to_needs_human_when_no_attempt_is_left(
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    build_node_recovery: BuildNodeRecovery,
    current_time: datetime,
) -> None:
    node = build_node(NodeState.ERRORED, 1, dead_pid, 0)
    node_recoveries = [
        build_node_recovery(True, timedelta()),
        build_node_recovery(True, timedelta()),
    ]

    async with database.open_session() as db_session:
        db_session.add_all([node, *node_recoveries])
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    audit_entry_repo = SqliteAuditEntryRepo(database)

    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=node_repo,
        node_recovery_repo=SqliteNodeRecoveryRepo(database),
        audit_entry_repo=audit_entry_repo,
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    recoverable_nodes = await service.get_recoverable_nodes(current_time)

    needs_human_node = await node_repo.read("A")
    audit_entries = await audit_entry_repo.get_all()
    assert needs_human_node is not None
    assert (recoverable_nodes, needs_human_node.state, audit_entries[0].note) == (
        [],
        NodeState.NEEDS_HUMAN.value,
        format_label(LABELS["outOfRecoveryAttempts"], {"count": 2}),
    )


async def test_get_recoverable_nodes_writes_no_audit_entry_when_the_needs_human_node_has_no_attempt_left(
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    current_time: datetime,
) -> None:
    node = build_node(NodeState.NEEDS_HUMAN, 0, dead_pid, 0)
    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    audit_entry_repo = SqliteAuditEntryRepo(database)
    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=SqliteNodeRepo(database),
        node_recovery_repo=SqliteNodeRecoveryRepo(database),
        audit_entry_repo=audit_entry_repo,
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    recoverable_nodes = await service.get_recoverable_nodes(current_time)

    audit_entries = await audit_entry_repo.get_all()
    assert (recoverable_nodes, audit_entries) == ([], [])


@pytest.mark.parametrize(
    ("session_count", "elapsed_seconds", "is_due"),
    [
        (1, 599, False),
        (1, 600, True),
        (2, 1199, False),
        (2, 1200, True),
        (5, 3599, False),
        (5, 3600, True),
    ],
)
async def test_get_recoverable_nodes_delays_recovery_after_sessions_without_verdicts(
    session_count: int,
    elapsed_seconds: int,
    is_due: bool,
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    current_time: datetime,
) -> None:
    node = build_node(NodeState.ERRORED, 1, dead_pid, 1)
    node_ids_json = json.dumps([node.id])
    recovery_sessions = []
    for index in range(1, session_count + 1):
        started_at = current_time + timedelta(minutes=index)
        ended_at = started_at + timedelta(seconds=30)
        recovery_session = RecoverySession(
            session_token=f"recovery-{index}",
            started_at=started_at,
            ended_at=ended_at,
            node_ids=node_ids_json,
        )

        recovery_sessions.append(recovery_session)

    async with database.open_session() as db_session:
        db_session.add_all([node, *recovery_sessions])
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    node_recovery_repo = SqliteNodeRecoveryRepo(database)
    audit_entry_repo = SqliteAuditEntryRepo(database)

    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        audit_entry_repo=audit_entry_repo,
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    last_ended_at = current_time + timedelta(minutes=session_count, seconds=30)
    scan_at = last_ended_at + timedelta(seconds=elapsed_seconds)

    recoverable_nodes = await service.get_recoverable_nodes(scan_at)

    assert [recoverable.id for recoverable in recoverable_nodes] == (
        ["A"] if is_due else []
    )

    stored_node = await node_repo.read("A")
    assert stored_node is not None
    assert stored_node.recovery_attempts_allowed == 1
    assert stored_node.state == NodeState.ERRORED.value


@pytest.mark.parametrize("has_new_agent_session", [False, True])
async def test_get_recoverable_nodes_resets_the_delay_after_a_verdict_or_a_new_agent_session(
    has_new_agent_session: bool,
    database: SqliteDatabase,
    dead_pid: int,
    build_node: BuildNode,
    build_node_recovery: BuildNodeRecovery,
    current_time: datetime,
) -> None:
    node = build_node(NodeState.ERRORED, 1, dead_pid, 3)
    delay = timedelta()
    node_recovery = build_node_recovery(not has_new_agent_session, delay)
    node_recovery.detected_at = current_time + timedelta(seconds=75)

    if has_new_agent_session:
        assert node.agent is not None
        started_at = current_time + timedelta(minutes=2)
        agent_session = AgentSession(
            agent_id="agent-A",
            started_at=started_at,
            ended_at=started_at,
            pid=dead_pid,
            exit_code=1,
        )

        node.agent.sessions.append(agent_session)

    recovery_sessions = []
    for index in (1, 3, 4):
        node_ids = ["A"] if index != 4 else ["B"]
        node_ids_json = json.dumps(node_ids)

        started_at = current_time + timedelta(minutes=index)
        ended_at = started_at + timedelta(seconds=30)
        recovery_session = RecoverySession(
            session_token=f"recovery-{index}",
            started_at=started_at,
            ended_at=ended_at,
            node_ids=node_ids_json,
        )

        recovery_sessions.append(recovery_session)

    async with database.open_session() as db_session:
        db_session.add_all([node, node_recovery, *recovery_sessions])
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    node_recovery_repo = SqliteNodeRecoveryRepo(database)
    audit_entry_repo = SqliteAuditEntryRepo(database)

    recovery_session_repo = SqliteRecoverySessionRepo(database)
    dag_spec = DagSpec(name="demo", nodes=())
    service = RecoveryScanService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        audit_entry_repo=audit_entry_repo,
        recovery_session_repo=recovery_session_repo,
        dag_spec=dag_spec,
    )

    before_retry_at = current_time + timedelta(seconds=809)
    before_delay = await service.get_recoverable_nodes(before_retry_at)

    retry_at = current_time + timedelta(seconds=810)
    after_delay = await service.get_recoverable_nodes(retry_at)

    assert before_delay == []
    assert [recoverable.id for recoverable in after_delay] == ["A"]

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.recovery.recovery_dispatch_service import (
    RecoveryDispatchService,
)
from virgo_agentic_dag.services.recovery.recovery_prompt_composer import (
    RecoveryPromptComposer,
)
from virgo_agentic_dag.services.recovery.recovery_session_killer import (
    RecoverySessionKiller,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 9, 5, tzinfo=UTC)

BuildNode = Callable[[str], Node]
BuildOpenRecoverySession = Callable[[int], RecoverySession]


@pytest.fixture
def dead_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()

    return process.pid


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id: Node(
        id=node_id,
        state=NodeState.ERRORED.value,
        created_at=NOW,
        updated_at=NOW,
        recovery_attempts_allowed=1,
    )


@pytest.fixture
def build_open_recovery_session() -> BuildOpenRecoverySession:
    return lambda pid: RecoverySession(
        id=1, session_token="token-1", pid=pid, started_at=NOW, node_ids='["A"]'
    )


@pytest.fixture
def started_agent_session() -> AgentSession:
    return AgentSession(
        agent_id="recovery", started_at=NOW, triggered_by="launch", pid=4242
    )


async def test_dispatch_starts_a_single_session_when_two_nodes_fail(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    dag_spec = DagSpec(name="recovery", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([build_node("A"), build_node("B")], NOW)

    agent_launcher.launch.assert_awaited_once()
    assert agent_launcher.launch.await_args.args[2].name == "codex"

    recovery_session = recovery_session_repo.add.await_args.args[0]
    assert (
        tick_response.sessions_started,
        recovery_session.pid,
        recovery_session.get_node_ids(),
    ) == (1, 4242, ["A", "B"])


@pytest.mark.parametrize("elapsed_seconds", [0, 59])
async def test_dispatch_leaves_a_live_session_running_before_its_deadline(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    build_open_recovery_session: BuildOpenRecoverySession,
    elapsed_seconds: int,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = build_open_recovery_session(
        os.getpid()
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    recovery_session_killer = mocker.MagicMock(spec=RecoverySessionKiller)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    attempt_budget = AttemptBudget(session_timeout_seconds=60)
    dag_spec = DagSpec(name="recovery", nodes=(), caps=attempt_budget)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        recovery_session_killer=recovery_session_killer,
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    current_time = NOW + timedelta(seconds=elapsed_seconds)

    tick_response = await service.dispatch([build_node("A")], current_time)

    agent_launcher.launch.assert_not_awaited()
    recovery_session_killer.kill.assert_not_awaited()
    recovery_session_repo.close.assert_not_awaited()

    audit_entry_repo.save.assert_not_awaited()
    assert tick_response.sessions_started == 0


@pytest.mark.parametrize(
    ("elapsed_seconds", "started_at"), [(60, NOW), (61, NOW.replace(tzinfo=None))]
)
async def test_dispatch_ends_an_overdue_session_to_allow_a_later_batch(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
    elapsed_seconds: int,
    started_at: datetime,
) -> None:
    recovery_session = RecoverySession(
        id=1,
        session_token="token-1",
        pid=os.getpid(),
        started_at=started_at,
        node_ids='["A", "B"]',
    )

    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.side_effect = [recovery_session, None]

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A"), build_node("B")]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    recovery_session_killer = mocker.MagicMock(spec=RecoverySessionKiller)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    attempt_budget = AttemptBudget(session_timeout_seconds=60)
    dag_spec = DagSpec(name="recovery", nodes=(), caps=attempt_budget)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        recovery_session_killer=recovery_session_killer,
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    current_time = NOW + timedelta(seconds=elapsed_seconds)
    later_pass_time = current_time + timedelta(seconds=1)
    recoverable_nodes = [build_node("C")]

    overdue_response = await service.dispatch(recoverable_nodes, current_time)
    later_response = await service.dispatch(recoverable_nodes, later_pass_time)

    recovery_session_killer.kill.assert_awaited_once_with(
        recovery_session, current_time
    )

    assert overdue_response.sessions_started == 0

    recovery_session_repo.add.assert_awaited_once()
    new_recovery_session = recovery_session_repo.add.await_args.args[0]
    assert new_recovery_session.get_node_ids() == ["C"]
    assert later_response.sessions_started == 1

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    overdue_entries = [
        entry for entry in audit_entries if entry.created_at == current_time
    ]

    assert [(entry.node_id, entry.state) for entry in overdue_entries] == [
        ("A", NodeState.ERRORED.value),
        ("B", NodeState.ERRORED.value),
    ]

    assert all("timeout" in entry.note for entry in overdue_entries)


async def test_dispatch_closes_the_previous_session_when_its_process_is_dead(
    mocker: MockerFixture,
    tmp_path: Path,
    dead_pid: int,
    build_node: BuildNode,
    build_open_recovery_session: BuildOpenRecoverySession,
    started_agent_session: AgentSession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = build_open_recovery_session(
        dead_pid
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    dag_spec = DagSpec(name="recovery", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([build_node("A")], NOW)

    closed_recovery_session = recovery_session_repo.close.await_args.args[0]
    assert (closed_recovery_session.id, closed_recovery_session.ended_at) == (1, NOW)

    assert tick_response.sessions_started == 0
    agent_launcher.launch.assert_not_awaited()


async def test_dispatch_starts_nothing_when_no_node_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    dag_spec = DagSpec(name="recovery", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([], NOW)

    agent_launcher.launch.assert_not_awaited()
    assert tick_response.sessions_started == 0


async def test_dispatch_preserves_recovery_attempts_when_the_session_starts(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    dag_spec = DagSpec(name="recovery", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    nodes = [build_node("A"), build_node("B")]

    await service.dispatch(nodes, NOW)

    assert [node.recovery_attempts_allowed for node in nodes] == [1, 1]


async def test_dispatch_records_an_audit_entry_for_each_node_when_the_session_starts(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    dag_spec = DagSpec(name="recovery", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        recovery_session_killer=mocker.MagicMock(spec=RecoverySessionKiller),
        dag_spec=dag_spec,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    await service.dispatch([build_node("A"), build_node("B")], NOW)

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    audited_node_ids = [audit_entry.node_id for audit_entry in audit_entries]
    assert audited_node_ids == ["A", "B"]
    assert audit_entries[0].state == NodeState.ERRORED.value

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
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
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.recovery.recovery_dispatch_service import (
    RecoveryDispatchService,
)
from virgo_agentic_dag.services.recovery.recovery_prompt_composer import (
    RecoveryPromptComposer,
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
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
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


async def test_dispatch_starts_nothing_when_the_previous_session_process_is_alive(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    build_open_recovery_session: BuildOpenRecoverySession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = build_open_recovery_session(
        os.getpid()
    )
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([build_node("A")], NOW)

    agent_launcher.launch.assert_not_awaited()
    recovery_session_repo.close.assert_not_awaited()
    assert tick_response.sessions_started == 0


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
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([build_node("A")], NOW)

    closed_recovery_session = recovery_session_repo.close.await_args.args[0]
    assert (closed_recovery_session.id, closed_recovery_session.ended_at) == (1, NOW)
    assert tick_response.sessions_started == 1


async def test_dispatch_starts_nothing_when_no_node_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    tick_response = await service.dispatch([], NOW)

    agent_launcher.launch.assert_not_awaited()
    assert tick_response.sessions_started == 0


async def test_dispatch_spends_a_recovery_attempt_of_each_node_when_the_session_starts(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    recovery_session_repo = mocker.MagicMock(spec=RecoverySessionRepo)
    recovery_session_repo.find_open_session.return_value = None
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session
    node_repo = mocker.MagicMock(spec=NodeRepo)
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    await service.dispatch([build_node("A"), build_node("B")], NOW)

    spent_node_ids = [
        call.args[0] for call in node_repo.spend_recovery_attempt.await_args_list
    ]
    assert spent_node_ids == ["A", "B"]


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
    service = RecoveryDispatchService(
        recovery_session_repo=recovery_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        prompt_composer=mocker.MagicMock(spec=RecoveryPromptComposer),
        recovery_home=tmp_path,
    )

    await service.dispatch([build_node("A"), build_node("B")], NOW)

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    audited_node_ids = [audit_entry.node_id for audit_entry in audit_entries]
    assert audited_node_ids == ["A", "B"]
    assert audit_entries[0].state == NodeState.ERRORED.value

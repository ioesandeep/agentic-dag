import io
import os
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.infra.agent.agent_session_killer import (
    ABORTED_END_STATE,
    AgentSessionKiller,
)
from virgo_agentic_dag.infra.agent.process_group_killer import ProcessGroupKiller

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 2, tzinfo=UTC)

_LEADER = (
    "import subprocess, time; "
    "child = subprocess.Popen(['sleep', '30']); print(child.pid, flush=True); "
    "time.sleep(30)"
)

BuildSession = Callable[[str, int | None], AgentSession]


@pytest.fixture
def build_session() -> BuildSession:
    started_at = datetime.now(UTC)

    return lambda node_id, pid: AgentSession(
        id=7,
        agent_id=f"agent-{node_id}",
        started_at=started_at,
        pid=pid,
        agent=NodeAgent(id=f"agent-{node_id}", name="claude", node_id=node_id),
    )


def is_dead(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True

    return False


def wait_until_dead(pid: int) -> bool:
    deadline = time.monotonic() + 5
    while not is_dead(pid) and time.monotonic() < deadline:
        time.sleep(0.05)

    return is_dead(pid)


async def test_kills_the_whole_group_the_session_runs_as(
    mocker: MockerFixture, build_session: BuildSession
) -> None:
    leader = subprocess.Popen(
        ["python3", "-c", _LEADER],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    assert leader.stdout is not None
    child_pid = int(leader.stdout.readline())

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    process_killer = ProcessGroupKiller()
    killer = AgentSessionKiller(
        agent_session_repo=agent_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        process_killer=process_killer,
    )

    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, io.StringIO())
    token = bind_context(context)

    try:
        await killer.kill(build_session("A", leader.pid), NOW)
    finally:
        unbind_context(token)

    leader.wait(timeout=5)
    assert wait_until_dead(child_pid)
    agent_session_repo.close.assert_awaited_once()


async def test_records_the_full_ending_when_killing(
    mocker: MockerFixture, build_session: BuildSession
) -> None:
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    process_killer = ProcessGroupKiller()
    killer = AgentSessionKiller(
        agent_session_repo=agent_session_repo,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        process_killer=process_killer,
    )

    out = io.StringIO()
    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)

    try:
        await killer.kill(build_session("A", None), NOW)
    finally:
        unbind_context(token)

    agent_session_repo.close.assert_awaited_once()
    closed = agent_session_repo.close.await_args.args[0]
    assert closed.end_state == ABORTED_END_STATE
    assert closed.ended_at == NOW

    node_repo.update_state.assert_awaited_once_with("A", NodeState.NEEDS_HUMAN, NOW)

    audit_entry_repo.save.assert_awaited_once()
    saved = audit_entry_repo.save.await_args.args[0]
    assert saved.node_id == "A"
    assert saved.state == "needs_human"

    assert "A" in out.getvalue()


async def test_still_records_the_ending_when_the_group_is_already_gone(
    mocker: MockerFixture, build_session: BuildSession
) -> None:
    leader = subprocess.Popen(["sleep", "0"], start_new_session=True)
    leader.wait(timeout=5)

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    process_killer = ProcessGroupKiller()
    killer = AgentSessionKiller(
        agent_session_repo=agent_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        process_killer=process_killer,
    )

    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, io.StringIO())
    token = bind_context(context)

    try:
        await killer.kill(build_session("A", leader.pid), NOW)
    finally:
        unbind_context(token)

    agent_session_repo.close.assert_awaited_once()


@pytest.mark.parametrize("has_signal_permission", [False, True])
async def test_kill_closes_the_session_without_killing_a_different_process(
    mocker: MockerFixture, has_signal_permission: bool
) -> None:
    process_killer = mocker.MagicMock(spec=ProcessGroupKiller)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    killer = AgentSessionKiller(
        agent_session_repo=agent_session_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        process_killer=process_killer,
    )

    if not has_signal_permission:
        mocker.patch("os.kill", side_effect=PermissionError)

    node_agent = NodeAgent(id="agent-A", name="claude", node_id="A")
    pid = os.getpid()
    session = AgentSession(
        id=7,
        agent_id="agent-A",
        started_at=NOW,
        pid=pid,
        agent=node_agent,
    )

    command = AbortCommand(dag_name="demo")
    context = ApplicationContext(command, io.StringIO())
    token = bind_context(context)

    try:
        await killer.kill(session, NOW)
    finally:
        unbind_context(token)

    process_killer.kill.assert_not_called()

    agent_session_repo.close.assert_awaited_once()

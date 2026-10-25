from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.learning.learning_dispatch_service import (
    LearningDispatchService,
)
from virgo_agentic_dag.services.learning.learning_prompt_composer import (
    LearningPromptComposer,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 9, 9, tzinfo=UTC)

BuildNode = Callable[[str], Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id: Node(
        id=node_id,
        state=NodeState.MERGED.value,
        created_at=NOW,
        updated_at=NOW,
        recovery_attempts_allowed=1,
        pull_request_settled_at=NOW,
    )


@pytest.fixture
def started_agent_session() -> AgentSession:
    return AgentSession(
        agent_id="learning", started_at=NOW, triggered_by="launch", pid=4242
    )


async def test_dispatch_starts_a_single_session_when_two_nodes_are_due_for_learning_extraction(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = True
    extraction_lock.acquire.return_value = True
    extraction_lock.get_session_node_ids.return_value = []

    settled_nodes = [build_node("A"), build_node("B")]
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_due_for_learning_extraction.return_value = settled_nodes

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    dag_spec = DagSpec(name="learning", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        process_killer=mocker.MagicMock(spec=ProcessKiller),
        dag_spec=dag_spec,
        run_home=tmp_path,
    )

    tick_response = await service.dispatch(NOW)

    node_repo.record_learnings_extracted.assert_awaited_once_with(settled_nodes, NOW)
    extraction_lock.record_session_pid.assert_awaited_once_with(4242, ["A", "B"])

    learning_agent = agent_launcher.launch.await_args.args[2]

    assert learning_agent.name == "codex"

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    audited_node_ids = [audit_entry.node_id for audit_entry in audit_entries]

    assert (
        tick_response.sessions_started,
        learning_agent.worktree.absolute_path,
        extraction_lock.record_session_pid.await_args.args[0],
        audited_node_ids,
    ) == (1, str(tmp_path / "learning"), 4242, ["A", "B"])


async def test_dispatch_does_not_start_a_session_when_the_extraction_lock_is_not_free(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = False
    extraction_lock.get_written_at.return_value = NOW

    attempt_budget = AttemptBudget(session_timeout_seconds=60)
    dag_spec = DagSpec(
        name="learning",
        nodes=(),
        executor_agent=ExecutorAgent.CODEX,
        caps=attempt_budget,
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    process_killer = mocker.MagicMock(spec=ProcessKiller)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        process_killer=process_killer,
        dag_spec=dag_spec,
        run_home=tmp_path,
    )

    current_time = NOW + timedelta(seconds=59)

    tick_response = await service.dispatch(current_time)

    agent_launcher.launch.assert_not_awaited()
    process_killer.kill.assert_not_called()
    extraction_lock.release.assert_not_awaited()

    node_repo.record_learnings_extracted.assert_not_awaited()
    assert tick_response.sessions_started == 0


async def test_dispatch_does_not_start_a_session_when_no_nodes_are_due_for_learning_extraction(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = True
    extraction_lock.get_session_node_ids.return_value = []

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_due_for_learning_extraction.return_value = []

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    dag_spec = DagSpec(name="learning", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        process_killer=mocker.MagicMock(spec=ProcessKiller),
        dag_spec=dag_spec,
        run_home=tmp_path,
    )

    tick_response = await service.dispatch(NOW)

    agent_launcher.launch.assert_not_awaited()
    extraction_lock.acquire.assert_not_awaited()
    assert tick_response.sessions_started == 0


@pytest.mark.parametrize(("exit_code", "audited_node_ids"), [(7, ["A", "B"]), (0, [])])
async def test_dispatch_audits_extraction_failures_when_the_learning_session_exits(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    exit_code: int,
    audited_node_ids: list[str],
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = True
    extraction_lock.get_session_node_ids.return_value = ["A", "B"]

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A"), build_node("B")]
    node_repo.get_nodes_due_for_learning_extraction.return_value = []

    exit_path = tmp_path / "learning.exit"
    exit_path.write_text(f"{exit_code}\n", encoding="utf-8")

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    dag_spec = DagSpec(name="learning", nodes=(), executor_agent=ExecutorAgent.CODEX)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        agent_launcher=mocker.MagicMock(spec=AgentLauncher),
        process_killer=mocker.MagicMock(spec=ProcessKiller),
        dag_spec=dag_spec,
        run_home=tmp_path,
    )

    await service.dispatch(NOW)

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    audit_notes = [(entry.node_id, entry.note) for entry in audit_entries]
    expected_note = (
        "its pull request learnings were not extracted because the learning session "
        f"exited with code {exit_code}"
    )

    assert audit_notes == [(node_id, expected_note) for node_id in audited_node_ids]
    node_repo.record_learnings_extracted.assert_not_awaited()
    extraction_lock.release.assert_awaited_once_with()


async def test_dispatch_kills_an_overdue_session_and_allows_a_later_learning_session(
    mocker: MockerFixture,
    tmp_path: Path,
    build_node: BuildNode,
    started_agent_session: AgentSession,
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.side_effect = [False, True]
    extraction_lock.acquire.return_value = True

    extraction_lock.get_written_at.return_value = NOW
    extraction_lock.get_live_session_pid.return_value = 4242
    extraction_lock.get_session_node_ids.side_effect = [["A", "B"], []]

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A"), build_node("B")]

    settled_nodes = [build_node("C")]
    node_repo.get_nodes_due_for_learning_extraction.return_value = settled_nodes

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session

    attempt_budget = AttemptBudget(session_timeout_seconds=60)
    dag_spec = DagSpec(
        name="learning",
        nodes=(),
        executor_agent=ExecutorAgent.CODEX,
        caps=attempt_budget,
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    process_killer = mocker.MagicMock(spec=ProcessKiller)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        process_killer=process_killer,
        dag_spec=dag_spec,
        run_home=tmp_path,
    )

    deadline = NOW + timedelta(seconds=60)
    later_pass_time = deadline + timedelta(seconds=1)

    overdue_response = await service.dispatch(deadline)
    later_response = await service.dispatch(later_pass_time)

    process_killer.kill.assert_called_once_with(4242)
    extraction_lock.release.assert_awaited_once_with()
    assert (overdue_response.sessions_started, later_response.sessions_started) == (
        0,
        1,
    )

    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    failed_node_ids = [entry.node_id for entry in audit_entries if "137" in entry.note]

    assert failed_node_ids == ["A", "B"]
    node_repo.record_learnings_extracted.assert_awaited_once_with(
        settled_nodes, later_pass_time
    )

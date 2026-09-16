from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
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
    settled_nodes = [build_node("A"), build_node("B")]
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_due_for_learning_extraction.return_value = settled_nodes
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = started_agent_session
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        run_home=tmp_path,
    )

    tick_response = await service.dispatch(NOW)

    node_repo.record_learnings_extracted.assert_awaited_once_with(settled_nodes, NOW)
    learning_agent = agent_launcher.launch.await_args.args[2]
    assert learning_agent.name == "codex"
    audit_entries = [call.args[0] for call in audit_entry_repo.save.await_args_list]
    audited_node_ids = [audit_entry.node_id for audit_entry in audit_entries]
    assert (
        tick_response.sessions_started,
        learning_agent.worktree.absolute_path,
        extraction_lock.record_session_pid.call_args.args[0],
        audited_node_ids,
    ) == (1, str(tmp_path / "learning"), 4242, ["A", "B"])


async def test_dispatch_does_not_start_a_session_when_the_extraction_lock_is_not_free(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = False
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        run_home=tmp_path,
    )

    tick_response = await service.dispatch(NOW)

    agent_launcher.launch.assert_not_awaited()
    node_repo.record_learnings_extracted.assert_not_awaited()
    assert tick_response.sessions_started == 0


async def test_dispatch_does_not_start_a_session_when_no_nodes_are_due_for_learning_extraction(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    extraction_lock = mocker.MagicMock(spec=ExtractionLock)
    extraction_lock.is_free.return_value = True
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_due_for_learning_extraction.return_value = []
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=mocker.MagicMock(spec=LearningPromptComposer),
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        agent_launcher=agent_launcher,
        executor_agent=ExecutorAgent.CODEX,
        run_home=tmp_path,
    )

    tick_response = await service.dispatch(NOW)

    agent_launcher.launch.assert_not_awaited()
    extraction_lock.acquire.assert_not_called()
    assert tick_response.sessions_started == 0

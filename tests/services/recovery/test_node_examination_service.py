import io
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.command.examine_command import ExamineCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.agent.claude_transcript_locator import (
    ClaudeTranscriptLocator,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.recovery.node_examination_service import (
    NodeExaminationService,
)

pytestmark = pytest.mark.behavior


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 5, tzinfo=UTC)


@pytest.fixture
def command() -> ExamineCommand:
    return ExamineCommand(dag_path=Path("dag.toml"), node_id="A")


@pytest.fixture
def out(command: ExamineCommand) -> Iterator[io.StringIO]:
    out = io.StringIO()
    token = bind_context(ApplicationContext(command, out))

    yield out

    unbind_context(token)


@pytest.fixture
def errored_node(now: datetime) -> Node:
    return Node(
        id="A",
        state=NodeState.ERRORED.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            resume_token="token-A",
            node_id="A",
            worktree=WorkTree(
                name="A", absolute_path="/ws/A", branch="feat/a", created_at=now
            ),
            sessions=[
                AgentSession(
                    id=7,
                    agent_id="agent-A",
                    started_at=now,
                    ended_at=now,
                    end_state=SessionStatus.OVERDUE.value,
                    triggered_by="wake",
                    pid=os.getpid(),
                    exit_code=137,
                    log_tail="Error: Reached max turns (120)",
                )
            ],
        ),
    )


async def test_examine_prints_the_row_and_the_latest_session_when_the_node_has_a_latest_session(
    mocker: MockerFixture, command: ExamineCommand, out: io.StringIO, errored_node: Node
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = errored_node
    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    node_recovery_repo.count_by_node_id.return_value = 1
    node_recovery_repo.get_newest_recovery_by_node_id.return_value = NodeRecovery(
        node_id="A",
        session_id=7,
        detected_at=errored_node.updated_at,
        cause=RecoveryCauseEnum.TURN_CAP_REACHED.value,
        recoverable=True,
        recover_at=errored_node.updated_at,
        action="woke it",
    )
    service = NodeExaminationService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        transcript_locators={ExecutorAgent.CLAUDE: ClaudeTranscriptLocator()},
    )

    exit_code = await service.examine(command)

    expected_fragments = [
        "node\tA\terrored",
        "worktree\t/ws/A\texists False\treclaimed False\tbranch feat/a\tpull request none",
        "session\t7\twake",
        "exit 137\tprocess alive True",
        "overdue sessions\t1",
        "-ws-A/token-A.jsonl",
        "Error: Reached max turns (120)",
        "recovery attempts left\t2\trows recorded\t1",
        "newest recovery\tturn_cap_reached\trecoverable True",
    ]
    output = out.getvalue()
    missing_fragments = [
        fragment for fragment in expected_fragments if fragment not in output
    ]
    assert exit_code is ExitCode.SUCCESS
    assert missing_fragments == []


async def test_examine_prints_none_for_the_worktree_and_session_when_the_node_never_started(
    mocker: MockerFixture, command: ExamineCommand, out: io.StringIO, now: datetime
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = Node(
        id="A",
        state=NodeState.ERRORED.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=3,
    )
    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    node_recovery_repo.count_by_node_id.return_value = 0
    node_recovery_repo.get_newest_recovery_by_node_id.return_value = None
    service = NodeExaminationService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        transcript_locators={ExecutorAgent.CLAUDE: ClaudeTranscriptLocator()},
    )

    exit_code = await service.examine(command)

    assert exit_code is ExitCode.SUCCESS
    assert "worktree\tnone\n" in out.getvalue()
    assert "session\tnone\n" in out.getvalue()


async def test_examine_fails_when_the_node_is_not_in_the_run(
    mocker: MockerFixture, command: ExamineCommand, out: io.StringIO
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = None
    service = NodeExaminationService(
        node_repo=node_repo,
        node_recovery_repo=mocker.MagicMock(spec=NodeRecoveryRepo),
        transcript_locators={},
    )

    exit_code = await service.examine(command)

    assert exit_code is ExitCode.FAILURE
    assert "A is not a node of this run" in out.getvalue()

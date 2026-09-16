import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.web.mappers.codex_transcript_mapper import (
    to_conversation_message_responses,
)
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.agent.codex_agent_launcher import CodexAgentLauncher
from virgo_agentic_dag.infra.agent.codex_transcript_locator import (
    CodexTranscriptLocator,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (
    SqliteDatabase,  # noqa: F401
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 12, tzinfo=UTC)
THREAD_ID = "d2b9dc7c-6c08-438e-876a-306492756634"
CODEX_SCRIPT = """
import json
import sys
print(json.dumps({"type": "thread.started", "thread_id": "d2b9dc7c-6c08-438e-876a-306492756634"}), flush=True)
print(json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": json.dumps(sys.argv[1:])}}), flush=True)
"""


@pytest.fixture
def agent(tmp_path: Path) -> NodeAgent:
    worktree_path = tmp_path / "A"
    worktree_path.mkdir()
    worktree = WorkTree(
        name="A", absolute_path=str(worktree_path), created_at=NOW, marks='{"pr":"1"}'
    )

    return NodeAgent(
        id="agent-A",
        name="codex",
        node_id="A",
        resume_token="dag-token",
        worktree=worktree,
    )


async def test_wake_resumes_the_existing_codex_thread_when_a_new_launcher_wakes_the_agent(
    mocker: MockerFixture, tmp_path: Path, agent: NodeAgent
) -> None:
    binary = tmp_path / "codex"
    binary.write_text(f"#!{sys.executable}\n{CODEX_SCRIPT}")
    binary.chmod(0o755)
    mocker.patch.object(CodexAgentLauncher, "_BINARY", str(binary))
    learnings_path = tmp_path / "learnings.md"
    learnings_path.write_text("Run the tests before pushing.")
    transcript_locator = CodexTranscriptLocator()
    launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=learnings_path,
        transcript_locator=transcript_locator,
    )
    graph_node = GraphNode(id="A")
    launched_session = await launcher.launch(graph_node, "Implement the feature", agent)
    await asyncio.to_thread(os.waitpid, launched_session.pid, 0)
    agent.sessions.append(launched_session)
    restarted_launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=learnings_path,
        transcript_locator=transcript_locator,
    )

    woken_session = await restarted_launcher.wake(graph_node, "Fix the review", agent)
    await asyncio.to_thread(os.waitpid, woken_session.pid, 0)

    transcript_path = transcript_locator.get_transcript_path(agent)
    transcript_lines = agent.get_transcript_lines(transcript_path)
    messages = to_conversation_message_responses(transcript_lines)
    arguments = json.loads(messages[-1].text)
    assert arguments[:2] == ["exec", "resume"]
    assert arguments[-2] == THREAD_ID
    assert "Run the tests before pushing." in arguments[-1]
    assert [message.role for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert len({message.uuid for message in messages}) == 4
    assert woken_session.marks_before == '{"pr":"1"}'
    assert agent.worktree.find_exit_code() == 0


async def test_wake_raises_worktree_error_when_codex_exits_before_recording_a_thread_id(
    mocker: MockerFixture, tmp_path: Path, agent: NodeAgent
) -> None:
    binary = tmp_path / "codex"
    binary.write_text("#!/bin/sh\necho 'authentication failed' >&2\nexit 9\n")
    binary.chmod(0o755)
    mocker.patch.object(CodexAgentLauncher, "_BINARY", str(binary))
    transcript_locator = CodexTranscriptLocator()
    launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=tmp_path / "memory.md",
        transcript_locator=transcript_locator,
    )
    graph_node = GraphNode(id="A")

    session = await launcher.launch(graph_node, "Implement the feature", agent)
    await asyncio.to_thread(os.waitpid, session.pid, 0)
    agent.sessions.append(session)

    assert agent.worktree.find_exit_code() == 9
    assert "authentication failed" in agent.worktree.find_log_tail()
    with pytest.raises(WorktreeError, match="did not record a thread ID"):
        await launcher.wake(graph_node, "Try again", agent)


@pytest.mark.parametrize("first_wake_fails", [False, True])
async def test_wake_resumes_the_adopted_thread_when_no_prior_wake_succeeds(
    mocker: MockerFixture, tmp_path: Path, agent: NodeAgent, first_wake_fails: bool
) -> None:
    agent.resume_token = THREAD_ID
    binary = tmp_path / "codex"
    binary.write_text(f"#!{sys.executable}\n{CODEX_SCRIPT}")
    binary.chmod(0o755)
    mocker.patch.object(CodexAgentLauncher, "_BINARY", str(binary))
    transcript_locator = CodexTranscriptLocator()
    launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=tmp_path / "memory.md",
        transcript_locator=transcript_locator,
    )
    graph_node = GraphNode(id="A")
    if first_wake_fails:
        binary.write_text("#!/bin/sh\necho 'authentication failed' >&2\nexit 9\n")
        failed_session = await launcher.wake(graph_node, "Address the review", agent)
        await asyncio.to_thread(os.waitpid, failed_session.pid, 0)
        agent.sessions.append(failed_session)
        binary.write_text(f"#!{sys.executable}\n{CODEX_SCRIPT}")

    session = await launcher.wake(graph_node, "Address the review", agent)
    await asyncio.to_thread(os.waitpid, session.pid, 0)

    transcript_path = transcript_locator.get_transcript_path(agent)
    transcript_lines = agent.get_transcript_lines(transcript_path)
    messages = to_conversation_message_responses(transcript_lines)
    arguments = json.loads(messages[-1].text)
    assert arguments[-2:] == [THREAD_ID, "Address the review"]


async def test_launch_records_exit_code_127_when_the_codex_binary_is_missing(
    mocker: MockerFixture, tmp_path: Path, agent: NodeAgent
) -> None:
    mocker.patch.object(CodexAgentLauncher, "_BINARY", str(tmp_path / "missing-codex"))
    transcript_locator = CodexTranscriptLocator()
    launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=tmp_path / "memory.md",
        transcript_locator=transcript_locator,
    )

    session = await launcher.launch(GraphNode(id="A"), "Implement the feature", agent)
    await asyncio.to_thread(os.waitpid, session.pid, 0)

    assert agent.worktree.find_exit_code() == 127
    assert "Codex execution failed" in agent.worktree.find_log_tail()


async def test_supervise_reports_overdue_when_the_deadline_passes_and_finished_when_stopped(
    mocker: MockerFixture, tmp_path: Path, agent: NodeAgent
) -> None:
    binary = tmp_path / "codex"
    binary.write_text("#!/bin/sh\nexec sleep 60\n")
    binary.chmod(0o755)
    mocker.patch.object(CodexAgentLauncher, "_BINARY", str(binary))
    transcript_locator = CodexTranscriptLocator()
    launcher = CodexAgentLauncher(
        timeout_seconds=30,
        learnings_path=tmp_path / "memory.md",
        transcript_locator=transcript_locator,
    )
    session = await launcher.launch(GraphNode(id="A"), "Implement the feature", agent)
    try:
        assert await launcher.supervise(session) is SessionStatus.ALIVE
        session.started_at = datetime(2020, 1, 1, tzinfo=UTC)
        assert await launcher.supervise(session) is SessionStatus.OVERDUE
    finally:
        await launcher.stop(session)
        await asyncio.to_thread(os.waitpid, session.pid, 0)

    assert await launcher.supervise(session) is SessionStatus.FINISHED

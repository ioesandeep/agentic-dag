import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.agent.claude_agent_launcher import ClaudeAgentLauncher

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 15, tzinfo=UTC)


@pytest.fixture
def agent(tmp_path: Path) -> NodeAgent:
    agent = NodeAgent(id="agent-A", name="claude", node_id="A", resume_token="token-A")
    agent.node = Node(id="A", state="running", created_at=NOW, updated_at=NOW)
    agent.worktree = WorkTree(
        name="A", absolute_path=str(tmp_path / "A"), created_at=NOW
    )

    return agent


@pytest.fixture
def learnings_path(tmp_path: Path) -> Path:
    return tmp_path / "memory.md"


@pytest.fixture
def popen(mocker: MockerFixture) -> MagicMock:
    spawned = mocker.patch.object(subprocess, "Popen")
    spawned.return_value.pid = 4242

    return spawned


async def test_launches_with_the_turn_limit_it_was_given(
    agent: NodeAgent, popen: MagicMock, learnings_path: Path
) -> None:
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.launch(GraphNode(id="A"), "do the work", agent)

    argv = popen.call_args.args[0]
    assert argv[argv.index("--max-turns") + 1] == "40"


async def test_wakes_with_the_turn_limit_it_was_given(
    agent: NodeAgent, popen: MagicMock, learnings_path: Path
) -> None:
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.wake(GraphNode(id="A"), "the check failed", agent)

    argv = popen.call_args.args[0]
    assert argv[argv.index("--max-turns") + 1] == "40"


async def test_launch_passes_the_node_exit_file_path_immediately_before_claude(
    agent: NodeAgent, popen: MagicMock, tmp_path: Path, learnings_path: Path
) -> None:
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.launch(GraphNode(id="A"), "do the work", agent)

    argv = popen.call_args.args[0]
    assert argv[:2] == ["sh", "-c"]
    assert argv[argv.index("claude") - 1] == str(tmp_path / "A.exit")


async def test_wake_passes_the_node_exit_file_path_immediately_before_claude(
    agent: NodeAgent, popen: MagicMock, tmp_path: Path, learnings_path: Path
) -> None:
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.wake(GraphNode(id="A"), "the check failed", agent)

    argv = popen.call_args.args[0]
    assert argv[:2] == ["sh", "-c"]
    assert argv[argv.index("claude") - 1] == str(tmp_path / "A.exit")


async def test_wake_removes_the_node_exit_file_when_it_exists(
    agent: NodeAgent, popen: MagicMock, tmp_path: Path, learnings_path: Path
) -> None:
    previous_exit_path = tmp_path / "A.exit"
    previous_exit_path.write_text("137\n")
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.wake(GraphNode(id="A"), "the check failed", agent)

    assert not previous_exit_path.exists()


async def test_wake_records_the_worktree_marks_from_the_previous_session(
    agent: NodeAgent, popen: MagicMock, learnings_path: Path
) -> None:
    agent.worktree.marks = '{"pr": "412"}'
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    session = await launcher.wake(GraphNode(id="A"), "the check failed", agent)

    assert session.marks_before == '{"pr": "412"}'


async def test_launch_appends_the_run_learnings_to_the_prompt(
    agent: NodeAgent, popen: MagicMock, learnings_path: Path
) -> None:
    learnings_path.write_text("Name a test after its subject.\n")
    launcher = ClaudeAgentLauncher(
        timeout_seconds=1800, max_turns=40, learnings_path=learnings_path
    )

    await launcher.launch(GraphNode(id="A"), "do the work", agent)

    argv = popen.call_args.args[0]
    assert argv[-1].startswith("do the work")
    assert "Name a test after its subject." in argv[-1]

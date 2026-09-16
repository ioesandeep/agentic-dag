from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 15, tzinfo=UTC)
SESSION_ID = "session-alpha"
WORKTREE_PATH = "/ws/alpha/seed"
TRANSCRIPT_LINE = '{"type": "user", "uuid": "user-1"}'
OLDER_LINE = "older"
OLDER_LINE_COUNT = 20


@pytest.fixture
def build_agent() -> Callable[[str], NodeAgent]:
    return lambda name: NodeAgent(
        id="agent-seed",
        name=name,
        node_id="seed",
        resume_token=SESSION_ID,
        worktree=WorkTree(
            name="alpha-seed", absolute_path=WORKTREE_PATH, created_at=NOW
        ),
    )


@pytest.fixture
def session_path(tmp_path: Path) -> Path:
    return tmp_path / f"{SESSION_ID}.jsonl"


@pytest.fixture
def write_session_file(session_path: Path) -> Callable[[str], None]:
    return lambda body: session_path.write_text(body, encoding="utf-8")


def test_node_agent_returns_the_transcript_lines_when_the_session_file_exists(
    build_agent: Callable[[str], NodeAgent],
    write_session_file: Callable[[str], None],
    session_path: Path,
) -> None:
    write_session_file(f"{TRANSCRIPT_LINE}\n")
    agent = build_agent("claude")

    transcript_lines = agent.get_transcript_lines(session_path)

    assert transcript_lines == [TRANSCRIPT_LINE]


@pytest.mark.parametrize(
    ("byte_limit", "kept_older_line_count"),
    [
        pytest.param(63, 4, id="cut_inside_a_line"),
        pytest.param(64, 5, id="cut_at_a_line_start"),
    ],
)
def test_node_agent_returns_whole_lines_when_the_session_file_runs_past_the_limit(
    mocker: MockerFixture,
    build_agent: Callable[[str], NodeAgent],
    write_session_file: Callable[[str], None],
    session_path: Path,
    byte_limit: int,
    kept_older_line_count: int,
) -> None:
    mocker.patch(
        "virgo_agentic_dag.domain.persistence.entities.node_agent.TRANSCRIPT_BYTE_LIMIT",
        byte_limit,
    )
    write_session_file(f"{OLDER_LINE}\n" * OLDER_LINE_COUNT + TRANSCRIPT_LINE)
    agent = build_agent("claude")

    transcript_lines = agent.get_transcript_lines(session_path)

    assert transcript_lines == [OLDER_LINE] * kept_older_line_count + [TRANSCRIPT_LINE]


def test_node_agent_returns_no_lines_when_the_session_file_is_gone(
    build_agent: Callable[[str], NodeAgent], session_path: Path
) -> None:
    agent = build_agent("claude")

    transcript_lines = agent.get_transcript_lines(session_path)

    assert transcript_lines == []

from datetime import UTC, datetime
from pathlib import Path

import pytest
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.learning.learning_prompt_composer import (
    LearningPromptComposer,
)

pytestmark = pytest.mark.behavior


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 8, tzinfo=UTC)


@pytest.fixture
def repo_slug() -> str:
    return "virgofyi/virgo"


@pytest.fixture
def learnings_path() -> Path:
    return Path("/runs/demo/memory.md")


@pytest.fixture
def merged_node(now: datetime) -> Node:
    return Node(
        id="A",
        title="Add the extraction lock",
        state=NodeState.MERGED.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            resume_token="token-A",
            node_id="A",
            worktree=WorkTree(
                name="A",
                absolute_path="/ws/A",
                branch="feat/a",
                pr_number=237,
                created_at=now,
            ),
        ),
    )


@pytest.fixture
def needs_human_node(now: datetime) -> Node:
    return Node(
        id="B",
        title="Record when a pull request settled",
        state=NodeState.NEEDS_HUMAN.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-B",
            name="claude",
            resume_token="token-B",
            node_id="B",
            worktree=WorkTree(
                name="B",
                absolute_path="/ws/B",
                branch="feat/b",
                pr_number=238,
                created_at=now,
            ),
        ),
    )


def test_compose_prompt_states_the_runbook_and_every_node_when_two_nodes_settle(
    merged_node: Node, needs_human_node: Node, learnings_path: Path, repo_slug: str
) -> None:
    composer = LearningPromptComposer(learnings_path, repo_slug)

    prompt = composer.compose_prompt([merged_node, needs_human_node])

    expected_fragments = [
        "# Learning runbook",
        f"`{repo_slug}`",
        f"`{learnings_path}`",
        "## Node `A`",
        "title: Add the extraction lock",
        "state: `merged`",
        "pull request: #237",
        "## Node `B`",
        "state: `needs_human`",
        "pull request: #238",
    ]
    missing_fragments = [
        fragment for fragment in expected_fragments if fragment not in prompt
    ]
    assert missing_fragments == []


def test_compose_prompt_omits_the_node_when_it_has_no_pull_request(
    learnings_path: Path, repo_slug: str, now: datetime
) -> None:
    composer = LearningPromptComposer(learnings_path, repo_slug)
    node = Node(
        id="A",
        title="Add the extraction lock",
        state=NodeState.NEEDS_HUMAN.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            resume_token="token-A",
            node_id="A",
            worktree=WorkTree(
                name="A",
                absolute_path="/ws/A",
                branch="feat/a",
                pr_number=0,
                created_at=now,
            ),
        ),
    )

    prompt = composer.compose_prompt([node])

    assert "## Node `A`" not in prompt

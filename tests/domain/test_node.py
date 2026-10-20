from datetime import UTC, datetime

import pytest

from virgo_agentic_dag.config.constants import STOPPED_SESSION_END_STATE
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("end_state", "exit_code", "expected_has_failed"),
    [
        (SessionStatus.FINISHED.value, 0, False),
        (SessionStatus.FINISHED.value, 1, True),
        (SessionStatus.FINISHED.value, None, True),
        (SessionStatus.OVERDUE.value, 0, True),
        (SessionStatus.OVERDUE.value, None, True),
    ],
)
def test_has_failed_returns_false_only_when_a_resting_node_has_a_finished_session_with_exit_code_zero(
    end_state: str, exit_code: int | None, expected_has_failed: bool
) -> None:
    current_time = datetime(2026, 9, 4, tzinfo=UTC)
    session = AgentSession(
        agent_id="agent-A",
        started_at=current_time,
        ended_at=current_time,
        end_state=end_state,
        exit_code=exit_code,
    )

    agent = NodeAgent(id="agent-A", node_id="A", sessions=[session])
    node = Node(id="A", state=NodeState.RESTING.value, agent=agent)

    has_failed = node.has_failed()

    assert has_failed is expected_has_failed


@pytest.mark.parametrize("has_agent", [False, True])
def test_can_recover_returns_false_when_the_node_has_no_session(
    has_agent: bool,
) -> None:
    agent = NodeAgent(id="agent-A", node_id="A", sessions=[]) if has_agent else None
    node = Node(
        id="A",
        state=NodeState.NEEDS_HUMAN.value,
        recovery_attempts_allowed=1,
        agent=agent,
    )

    can_recover = node.can_recover()

    assert can_recover is False


def test_can_recover_returns_false_when_a_person_stops_the_session() -> None:
    current_time = datetime(2026, 9, 4, tzinfo=UTC)
    session = AgentSession(
        agent_id="agent-A",
        started_at=current_time,
        ended_at=current_time,
        end_state=STOPPED_SESSION_END_STATE,
        exit_code=None,
    )

    agent = NodeAgent(id="agent-A", node_id="A", sessions=[session])
    node = Node(
        id="A",
        state=NodeState.NEEDS_HUMAN.value,
        recovery_attempts_allowed=1,
        agent=agent,
    )

    can_recover = node.can_recover()

    assert can_recover is False

from datetime import UTC, datetime

import pytest
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.infra.persistence.memory.inmemory_node_repo import (
    InMemoryNodeRepo,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 9, tzinfo=UTC)
LATER = datetime(2026, 8, 10, tzinfo=UTC)
TITLED = GraphNode(id="A", title="rename the token", name="Cancer")


async def test_ensure_rows_records_the_title_of_the_node_it_seeds() -> None:
    repo = InMemoryNodeRepo()

    await repo.ensure_rows([TITLED], NOW)

    row = await repo.read("A")
    assert row is not None and row.title == "rename the token"


async def test_update_state_keeps_the_title() -> None:
    repo = InMemoryNodeRepo()
    await repo.ensure_rows([TITLED], NOW)

    await repo.update_state("A", NodeState.IN_PROGRESS, LATER)

    row = await repo.read("A")
    assert row is not None and row.title == "rename the token"

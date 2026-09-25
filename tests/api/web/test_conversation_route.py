import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from itertools import accumulate
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.controllers.node_action_controller import (
    NodeActionController,
)
from virgo_agentic_dag.api.web.routes.conversation_route import ConversationRoute
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
from virgo_agentic_dag.api.web.routes.node_action_route import NodeActionRoute
from virgo_agentic_dag.api.web.routes.recovery_session_route import (
    RecoverySessionRoute,
)
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.service.node_action_service import NodeActionService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.agent.claude_transcript_locator import (
    ClaudeTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.codex_transcript_locator import (
    CodexTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_agent_repo import (
    SqliteNodeAgentRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

STARTED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
RECORDED_AT = "2026-08-15T09:00:00+00:00"
SMALL_BLOCK_SIZE_BYTES = 64
CONVERSATION_PATH = "/api/dags/alpha/seed/conversation"


@pytest.fixture
def dag_home(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root",
        return_value=tmp_path,
    )
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )
    mocker.patch(
        "virgo_agentic_dag.infra.agent.claude_transcript_locator.PROJECTS_HOME",
        tmp_path / "projects",
    )
    mocker.patch(
        "virgo_agentic_dag.infra.agent.transcript_page_reader.TRANSCRIPT_BLOCK_SIZE_BYTES",
        SMALL_BLOCK_SIZE_BYTES,
    )

    return tmp_path


@pytest.fixture
async def database(dag_home: Path) -> AsyncGenerator[SqliteDatabase]:
    dag_home.joinpath("alpha").mkdir()
    dag_home.joinpath("alpha", "dag.toml").write_text(
        "name = 'alpha'\n[[nodes]]\nid = 'seed'\n", encoding="utf-8"
    )
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{dag_home / 'alpha' / 'db.sqlite3'}"
    )
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)

    yield database

    await database.dispose()


@pytest.fixture
def save_node_agent(
    dag_home: Path, database: SqliteDatabase
) -> Callable[[ExecutorAgent], Awaitable[NodeAgent]]:
    async def save(executor_agent: ExecutorAgent) -> NodeAgent:
        worktree = WorkTree(
            name="alpha-seed",
            absolute_path=str(dag_home / "ws" / "seed"),
            branch="feat/seed",
            created_at=STARTED_AT,
        )
        node_agent = NodeAgent(
            id="agent-seed",
            name=executor_agent.value,
            resume_token="token-seed",
            node_id="seed",
            worktree=worktree,
        )
        await SqliteNodeAgentRepo(database).save(node_agent)

        return node_agent

    return save


@pytest.fixture
def write_transcript() -> Callable[[Path, list[dict[str, Any]]], list[int]]:
    def write(transcript_path: Path, records: list[dict[str, Any]]) -> list[int]:
        transcript_lines = [json.dumps(record) + "\n" for record in records]
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text("".join(transcript_lines), encoding="utf-8")
        line_ends = list(accumulate(len(line) for line in transcript_lines))

        return [0, *line_ends[:-1]]

    return write


@pytest.fixture
def build_claude_record() -> Callable[[str, list[dict[str, Any]]], dict[str, Any]]:
    return lambda role, content: {
        "type": role,
        "uuid": f"{role}-record",
        "timestamp": RECORDED_AT,
        "isSidechain": False,
        "message": {"role": role, "content": content},
    }


@pytest.fixture
def build_codex_record() -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    return lambda record_type, item: {
        "type": record_type,
        "timestamp": RECORDED_AT,
        "execution_id": "turn-1",
        "item": item,
    }


@pytest.fixture
def client(mocker: MockerFixture, dag_home: Path) -> TestClient:
    dag_controller = DagController(
        DagWebService(
            DagService(TomlDagLoader()),
            DagDatabaseRegistry(),
            mocker.MagicMock(spec=CodeRepo),
            {
                ExecutorAgent.CLAUDE: ClaudeTranscriptLocator(),
                ExecutorAgent.CODEX: CodexTranscriptLocator(),
            },
            TranscriptPageReader(),
        )
    )
    node_action_controller = NodeActionController(
        mocker.MagicMock(spec=NodeActionService)
    )
    application = WebApplicationFactory(
        dag_route=DagRoute(dag_controller),
        health_route=HealthRoute(HealthController()),
        memory_route=MemoryRoute(dag_controller),
        conversation_route=ConversationRoute(dag_controller),
        node_action_route=NodeActionRoute(node_action_controller),
        recovery_session_route=RecoverySessionRoute(dag_controller),
    ).build()

    return TestClient(application)


async def test_conversation_page_returns_the_older_page_of_the_same_session_with_a_null_cursor_when_the_next_cursor_is_followed(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    records = [
        build_claude_record("user", [{"type": "text", "text": "fix the build"}]),
        build_claude_record(
            "assistant", [{"type": "text", "text": "the build passes"}]
        ),
    ]
    write_transcript(transcript_path, records)

    newest_page = client.get(CONVERSATION_PATH, params={"limit": 1}).json()
    older_page = client.get(
        CONVERSATION_PATH,
        params={"before": newest_page["pagination"]["nextCursor"], "limit": 1},
    ).json()

    assert [message["text"] for message in newest_page["messages"]] == [
        "the build passes"
    ]
    assert [message["text"] for message in older_page["messages"]] == ["fix the build"]
    assert older_page["pagination"]["nextCursor"] is None
    assert (newest_page["sessionId"], older_page["sessionId"]) == (
        "token-seed",
        "token-seed",
    )


async def test_conversation_page_returns_a_distinct_id_for_each_message_when_a_record_contains_two_blocks(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    text_block = {"type": "text", "text": "running the tests"}
    tool_use_block = {"type": "tool_use", "id": "toolu-a", "name": "Bash", "input": {}}
    records = [build_claude_record("assistant", [text_block, tool_use_block])]
    write_transcript(transcript_path, records)

    response = client.get(CONVERSATION_PATH)

    assert [message["id"] for message in response.json()["messages"]] == [
        "0:1",
        "0:0",
    ]


async def test_conversation_page_returns_all_messages_from_the_boundary_record_when_older_records_exist_beyond_the_requested_limit(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    text_block = {"type": "text", "text": "running the tests"}
    tool_use_block = {"type": "tool_use", "id": "toolu-a", "name": "Bash", "input": {}}
    records = [
        build_claude_record("user", [{"type": "text", "text": "fix the build"}]),
        build_claude_record("assistant", [text_block, tool_use_block]),
        build_claude_record(
            "assistant", [{"type": "text", "text": "the build passes"}]
        ),
    ]
    record_offsets = write_transcript(transcript_path, records)

    response = client.get(CONVERSATION_PATH, params={"limit": 2})

    conversation_page = response.json()
    assert len(conversation_page["messages"]) == 3
    assert conversation_page["pagination"]["nextCursor"] == record_offsets[1]


@pytest.mark.parametrize(("limit", "tool_result"), [(2, "3 passed"), (1, "")])
async def test_conversation_page_returns_the_result_of_a_tool_call_at_its_newer_edge_only_when_the_result_is_within_the_look_ahead(
    limit: int,
    tool_result: str,
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    records = [
        build_claude_record("user", [{"type": "text", "text": "fix the build"}]),
        build_claude_record(
            "assistant",
            [{"type": "tool_use", "id": "toolu-a", "name": "Bash", "input": {}}],
        ),
        build_claude_record(
            "assistant",
            [{"type": "tool_use", "id": "toolu-b", "name": "Read", "input": {}}],
        ),
        build_claude_record(
            "user",
            [{"type": "tool_result", "tool_use_id": "toolu-a", "content": "3 passed"}],
        ),
    ]
    record_offsets = write_transcript(transcript_path, records)

    response = client.get(
        CONVERSATION_PATH, params={"before": record_offsets[2], "limit": limit}
    )

    newest_message = response.json()["messages"][0]
    assert (newest_message["toolName"], newest_message["toolResult"]) == (
        "Bash",
        tool_result,
    )


async def test_conversation_page_returns_the_latest_state_of_each_codex_item_when_its_records_span_a_page_boundary(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_codex_record: Callable[[str, dict[str, Any]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CODEX)
    transcript_path = CodexTranscriptLocator().get_transcript_path(node_agent)
    pytest_item = {"id": "item_0", "type": "command_execution", "command": "pytest"}
    ruff_item = {"id": "item_1", "type": "command_execution", "command": "ruff"}
    records = [
        {
            "type": "dag.prompt",
            "timestamp": RECORDED_AT,
            "execution_id": "turn-1",
            "text": "fix the build",
        },
        build_codex_record("item.started", pytest_item),
        build_codex_record("item.started", ruff_item),
        build_codex_record(
            "item.completed", {**pytest_item, "aggregated_output": "3 passed"}
        ),
        build_codex_record(
            "item.completed", {**ruff_item, "aggregated_output": "All checks passed"}
        ),
        build_codex_record(
            "item.completed",
            {"id": "item_2", "type": "agent_message", "text": "the build passes"},
        ),
    ]
    write_transcript(transcript_path, records)

    newest_page = client.get(CONVERSATION_PATH, params={"limit": 2}).json()
    older_page = client.get(
        CONVERSATION_PATH,
        params={"before": newest_page["pagination"]["nextCursor"], "limit": 2},
    ).json()

    assert [
        [message["text"] or message["toolResult"] for message in page["messages"]]
        for page in (newest_page, older_page)
    ] == [["the build passes", "All checks passed"], ["3 passed", "fix the build"]]


async def test_conversation_page_excludes_the_final_transcript_line_when_it_has_no_line_ending(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    records = [
        build_claude_record("assistant", [{"type": "text", "text": "the build passes"}])
    ]
    write_transcript(transcript_path, records)
    partial_record = build_claude_record("user", [{"type": "text", "text": "and"}])
    with transcript_path.open("a", encoding="utf-8") as transcript_file:
        transcript_file.write(json.dumps(partial_record))

    response = client.get(CONVERSATION_PATH)

    assert [message["text"] for message in response.json()["messages"]] == [
        "the build passes"
    ]


async def test_conversation_page_responds_404_when_the_cursor_is_past_the_end_of_the_transcript(
    client: TestClient,
    save_node_agent: Callable[[ExecutorAgent], Awaitable[NodeAgent]],
    write_transcript: Callable[[Path, list[dict[str, Any]]], list[int]],
    build_claude_record: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> None:
    node_agent = await save_node_agent(ExecutorAgent.CLAUDE)
    transcript_path = ClaudeTranscriptLocator().get_transcript_path(node_agent)
    records = [build_claude_record("user", [{"type": "text", "text": "fix the build"}])]
    write_transcript(transcript_path, records)
    past_end = transcript_path.stat().st_size + 1

    response = client.get(CONVERSATION_PATH, params={"before": past_end})

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"cursor {past_end} is past the end of the transcript of node "
        "seed in dag alpha"
    }


async def test_conversation_page_returns_an_empty_page_when_the_node_has_no_agent(
    client: TestClient, database: SqliteDatabase
) -> None:
    response = client.get(CONVERSATION_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "sessionId": "",
        "messages": [],
        "pagination": {"nextCursor": None, "perPage": 50},
    }


async def test_conversation_page_responds_404_when_the_dag_has_no_node_with_the_requested_id(
    client: TestClient, database: SqliteDatabase
) -> None:
    response = client.get("/api/dags/alpha/ghost/conversation")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "no node named ghost is in dag alpha on this host"
    }

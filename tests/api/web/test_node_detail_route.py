import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
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
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.agent.claude_transcript_locator import (
    ClaudeTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_agent_repo import (
    SqliteNodeAgentRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_slack_notification_repo import (
    SqliteSlackNotificationRepo,
)
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

STARTED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
WAKE_AT = datetime(2026, 8, 15, 9, 58, tzinfo=UTC)
RECOVER_AT = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)
REPO_URL = "https://git.example.com/acme/virgo"


@pytest.fixture
def dag_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    return tmp_path


@pytest.fixture
def write_graph(dag_home: Path) -> Callable[[str, str], None]:
    def write(dag_name: str, body: str) -> None:
        home = dag_home / dag_name
        home.mkdir(parents=True, exist_ok=True)
        home.joinpath("dag.toml").write_text(body, encoding="utf-8")

    return write


@pytest.fixture
async def open_database(
    dag_home: Path,
) -> AsyncGenerator[Callable[[str], Awaitable[SqliteDatabase]]]:
    opened: list[SqliteDatabase] = []

    async def open_for(dag_name: str) -> SqliteDatabase:
        db_path = dag_home / dag_name / "db.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        database = SqliteDatabase(engine)
        await database.upgrade_to_head()
        opened.append(database)

        return database

    yield open_for

    for database in opened:
        await database.dispose()


@pytest.fixture
def build_application(mocker: MockerFixture) -> Callable[[CodeRepo], FastAPI]:
    def build(code_repo: CodeRepo) -> FastAPI:
        dag_controller = DagController(
            DagWebService(
                DagService(TomlDagLoader()),
                DagDatabaseRegistry(),
                code_repo,
                {ExecutorAgent.CLAUDE: ClaudeTranscriptLocator()},
                TranscriptPageReader(),
            )
        )
        node_action_controller = NodeActionController(
            mocker.MagicMock(spec=NodeActionService)
        )

        return WebApplicationFactory(
            dag_route=DagRoute(dag_controller),
            health_route=HealthRoute(HealthController()),
            memory_route=MemoryRoute(dag_controller),
            conversation_route=ConversationRoute(dag_controller),
            node_action_route=NodeActionRoute(node_action_controller),
            recovery_session_route=RecoverySessionRoute(dag_controller),
        ).build()

    return build


async def test_node_detail_returns_what_the_dag_records_where_its_database_opens(
    mocker: MockerFixture,
    dag_home: Path,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph(
        "alpha",
        "name = 'alpha'\nbase_branch = 'develop'\n"
        f"project_root = '{dag_home / 'checkout'}'\n"
        "[[nodes]]\nid = 'seed'\ntitle = 'seed the table'\nname = 'Leo'\n"
        "instructions = 'Seed the accounts table.'\n"
        "[[nodes]]\nid = 'read'\ntitle = 'read the table'\ndepends_on = ['seed']\n",
    )
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows(
        [
            GraphNode(id="seed", title="seed the table", name="Leo"),
            GraphNode(id="read", title="read the table"),
        ],
        STARTED_AT,
    )
    await SqliteNodeRepo(database).update_state("seed", NodeState.RESTING, WAKE_AT)

    worktree = WorkTree(
        name="alpha-seed",
        absolute_path="/ws/alpha/seed",
        branch="feat/seed",
        pr_number=412,
        marks='{"pr": "412", "checks": "run-9"}',
        created_at=STARTED_AT,
    )
    agent_sessions = [
        AgentSession(
            started_at=STARTED_AT,
            ended_at=WAKE_AT,
            end_state="finished",
            triggered_by="launch",
        ),
        AgentSession(started_at=WAKE_AT, triggered_by="wake"),
    ]
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        worktree=worktree,
        sessions=agent_sessions,
    )
    await SqliteNodeAgentRepo(database).save(node_agent)

    audit_entry_repo = SqliteAuditEntryRepo(database)
    await audit_entry_repo.save(
        AuditEntry(
            node_id="seed",
            state="in_progress",
            note="its dependencies merged",
            created_at=STARTED_AT,
        )
    )
    await audit_entry_repo.save(
        AuditEntry(
            node_id="read", state="pending", note="waits on seed", created_at=STARTED_AT
        )
    )
    await audit_entry_repo.save(
        AuditEntry(
            node_id="seed", state="resting", note="opened #412", created_at=WAKE_AT
        )
    )
    await SqliteSlackNotificationRepo(database).save(
        SlackNotification(
            node_id="seed",
            channel="#alpha",
            thread_id="1755248400.000100",
            created_at=STARTED_AT,
        )
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_repo_url.return_value = REPO_URL

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/seed")

    assert response.status_code == 200
    node_response = response.json()
    assert node_response["worktree"]["signalMarks"] == {"pr": "412", "checks": "run-9"}
    assert [session["endState"] for session in node_response["sessions"]] == [
        "finished",
        "",
    ]
    assert [line["note"] for line in node_response["audits"]] == [
        "opened #412",
        "its dependencies merged",
    ]
    assert node_response["slackNotifications"][0]["threadId"] == "1755248400.000100"


async def test_node_detail_returns_the_messages_of_its_agent_session_when_the_last_line_is_partial(
    mocker: MockerFixture,
    tmp_path: Path,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    worktree = WorkTree(
        name="alpha-seed",
        absolute_path="/ws/alpha/seed",
        branch="feat/seed",
        created_at=STARTED_AT,
    )
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        worktree=worktree,
    )
    await SqliteNodeAgentRepo(database).save(node_agent)

    mocker.patch(
        "virgo_agentic_dag.infra.agent.claude_transcript_locator.PROJECTS_HOME",
        tmp_path,
    )
    session_home = tmp_path / "-ws-alpha-seed"
    session_home.mkdir(parents=True)
    user_record = {
        "type": "user",
        "uuid": "user-1",
        "timestamp": "2026-08-15T09:00:00.000Z",
        "isSidechain": False,
        "message": {"role": "user", "content": "hi"},
    }
    session_body = json.dumps(user_record) + '\n{"type": "assistant", "uu'
    session_home.joinpath("token-seed.jsonl").write_text(session_body, encoding="utf-8")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/seed")

    assert response.status_code == 200
    assert [message["uuid"] for message in response.json()["transcript"]] == ["user-1"]


def test_node_detail_responds_404_where_no_dag_has_the_name(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/ghost/seed")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "no node named seed is in dag ghost on this host"
    }


async def test_node_detail_responds_404_where_the_dag_has_no_node_with_the_id(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/ghost")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "no node named ghost is in dag alpha on this host"
    }


async def test_node_detail_returns_empty_collections_where_the_node_has_no_agent(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph(
        "alpha",
        "name = 'alpha'\n"
        "[[nodes]]\nid = 'seed'\ntitle = 'seed the table'\n"
        "[[nodes]]\nid = 'read'\ndepends_on = ['seed']\n",
    )
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows(
        [GraphNode(id="seed", title="seed the table"), GraphNode(id="read")],
        STARTED_AT,
    )
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/read")

    assert response.status_code == 200
    node_response = response.json()
    assert node_response["worktree"] is None
    assert (
        node_response["sessions"],
        node_response["audits"],
        node_response["slackNotifications"],
    ) == ([], [], [])


async def test_node_detail_returns_null_exit_code_and_recovery_when_the_node_has_no_agent(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/seed")

    assert response.status_code == 200
    node_response = response.json()
    assert (
        node_response["exitCode"],
        node_response["logTail"],
        node_response["nodeRecovery"],
    ) == (None, None, None)


async def test_node_detail_returns_the_newest_agent_sessions_recovery_when_the_session_fails(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    agent_sessions = [
        AgentSession(
            started_at=STARTED_AT,
            ended_at=WAKE_AT,
            end_state="finished",
            triggered_by="launch",
            exit_code=0,
        ),
        AgentSession(
            started_at=WAKE_AT,
            ended_at=RECOVER_AT,
            end_state="finished",
            triggered_by="wake",
            exit_code=137,
            log_tail="Error: Reached max turns (120)",
        ),
    ]
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        sessions=agent_sessions,
    )
    await SqliteNodeAgentRepo(database).save(node_agent)
    node_recovery = NodeRecovery(
        node_id="seed",
        session_id=2,
        detected_at=RECOVER_AT,
        cause=RecoveryCauseEnum.TURN_CAP_REACHED.value,
        recoverable=True,
        recover_at=RECOVER_AT,
        action="woke the node",
    )
    await SqliteNodeRecoveryRepo(database).add(node_recovery)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/seed")

    assert response.status_code == 200
    node_response = response.json()
    assert node_response["exitCode"] == 137
    assert node_response["logTail"] == "Error: Reached max turns (120)"
    assert node_response["nodeRecovery"]["cause"] == "turn_cap_reached"


async def test_node_detail_returns_no_recovery_when_the_newest_session_ends_cleanly(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    agent_session = AgentSession(
        started_at=STARTED_AT,
        ended_at=WAKE_AT,
        end_state="finished",
        triggered_by="launch",
        exit_code=0,
        log_tail="opened #412",
    )
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        sessions=[agent_session],
    )
    await SqliteNodeAgentRepo(database).save(node_agent)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha/seed")

    assert response.status_code == 200
    node_response = response.json()
    assert node_response["exitCode"] == 0
    assert node_response["nodeRecovery"] is None

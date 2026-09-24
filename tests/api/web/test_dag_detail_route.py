from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
from virgo_agentic_dag.api.web.service.dag_web_service import (
    AUDIT_TAIL_SIZE,
    DagWebService,
)
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
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
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

READ_ONLY_METHODS = {"GET", "HEAD"}
STARTED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
WAKE_AT = datetime(2026, 8, 15, 9, 58, tzinfo=UTC)
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
def build_application() -> Callable[[CodeRepo], FastAPI]:
    def build(code_repo: CodeRepo) -> FastAPI:
        dag_controller = DagController(
            DagWebService(
                DagService(TomlDagLoader()), DagDatabaseRegistry(), code_repo, {}
            )
        )

        return WebApplicationFactory(
            dag_route=DagRoute(dag_controller),
            health_route=HealthRoute(HealthController()),
            memory_route=MemoryRoute(dag_controller),
        ).build()

    return build


@pytest.fixture
def build_session() -> Callable[[str], AgentSession]:
    return lambda triggered_by: AgentSession(
        started_at=STARTED_AT, triggered_by=triggered_by
    )


@pytest.fixture
def build_agent() -> Callable[[str, WorkTree | None, list[AgentSession]], NodeAgent]:
    return lambda resume_token, worktree, sessions: NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token=resume_token,
        node_id="seed",
        worktree=worktree,
        sessions=sessions,
    )


async def test_dag_detail_returns_what_a_dag_records_where_its_database_opens(
    mocker: MockerFixture,
    dag_home: Path,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
    build_session: Callable[[str], AgentSession],
    build_agent: Callable[[str, WorkTree | None, list[AgentSession]], NodeAgent],
) -> None:
    write_graph(
        "alpha",
        "name = 'alpha'\nbase_branch = 'develop'\ntick_interval_seconds = 600\n"
        f"project_root = '{dag_home / 'checkout'}'\n"
        "[[nodes]]\nid = 'seed'\ntitle = 'seed the table'\nname = 'Leo'\n"
        "[[nodes]]\nid = 'read'\ndepends_on = ['seed']\n"
        "pr = 'https://github.com/acme/virgo/pull/7'\n"
        "[[nodes]]\nid = 'write'\n",
    )

    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows(
        [GraphNode(id="seed", title="seed the table", name="Leo")], STARTED_AT
    )
    await SqliteNodeRepo(database).update_state("seed", NodeState.RESTING, WAKE_AT)

    worktree = WorkTree(
        name="alpha-seed",
        absolute_path="/ws/alpha/seed",
        branch="feat/seed",
        pr_number=412,
        pr_url="https://git.example.com/acme/virgo/pull/412",
        created_at=STARTED_AT,
    )
    sessions = [build_session("launch"), build_session("wake")]
    agent = build_agent("token-seed", worktree, sessions)
    await SqliteNodeAgentRepo(database).save(agent)

    await SqliteAuditEntryRepo(database).save(
        AuditEntry(
            node_id="seed",
            state="in_progress",
            note="its dependencies merged",
            created_at=STARTED_AT,
        )
    )
    await SqliteAuditEntryRepo(database).save(
        AuditEntry(
            node_id="seed", state="resting", note="opened #412", created_at=WAKE_AT
        )
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha")

    assert response.status_code == 200
    assert response.json() == {
        "name": "alpha",
        "baseBranch": "develop",
        "tickIntervalSeconds": 600,
        "nodeCount": 3,
        "nodes": [
            {
                "id": "seed",
                "title": "seed the table",
                "agentName": "Leo",
                "state": "resting",
                "dependsOn": [],
                "updatedAt": "2026-08-15T09:58:00Z",
                "wakes": 1,
                "sessionId": "token-seed",
                "prUrl": "https://git.example.com/acme/virgo/pull/412",
                "prNumber": 412,
                "worktreeName": "alpha-seed",
                "branch": "feat/seed",
            },
            {
                "id": "read",
                "title": "",
                "agentName": "read",
                "state": "pending",
                "dependsOn": ["seed"],
                "updatedAt": None,
                "wakes": 0,
                "sessionId": "",
                "prUrl": "https://github.com/acme/virgo/pull/7",
                "prNumber": 7,
                "worktreeName": "",
                "branch": "",
            },
            {
                "id": "write",
                "title": "",
                "agentName": "write",
                "state": "pending",
                "dependsOn": [],
                "updatedAt": None,
                "wakes": 0,
                "sessionId": "",
                "prUrl": "",
                "prNumber": 0,
                "worktreeName": "",
                "branch": "",
            },
        ],
        "lastActivityAt": "2026-08-15T09:58:00Z",
        "isScheduled": False,
        "isWatching": False,
        "isReadable": True,
        "audit": [
            {
                "createdAt": "2026-08-15T09:58:00Z",
                "nodeId": "seed",
                "state": "resting",
                "note": "opened #412",
            },
            {
                "createdAt": "2026-08-15T09:00:00Z",
                "nodeId": "seed",
                "state": "in_progress",
                "note": "its dependencies merged",
            },
        ],
    }


def test_dag_detail_responds_404_where_no_dag_has_the_name(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/ghost")

    assert response.status_code == 404
    assert response.json() == {"detail": "no dag named ghost lives on this host"}


async def test_dag_detail_counts_only_wake_sessions_where_the_launch_is_recorded(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
    build_session: Callable[[str], AgentSession],
    build_agent: Callable[[str, WorkTree | None, list[AgentSession]], NodeAgent],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    sessions = [build_session("launch"), build_session("wake"), build_session("wake")]
    agent = build_agent("token-seed", None, sessions)
    await SqliteNodeAgentRepo(database).save(agent)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha")

    assert response.json()["nodes"][0]["wakes"] == 2


async def test_dag_detail_formats_the_pull_request_url_from_the_repository_url_when_the_work_tree_has_no_pull_request_url(
    mocker: MockerFixture,
    dag_home: Path,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
    build_agent: Callable[[str, WorkTree | None, list[AgentSession]], NodeAgent],
) -> None:
    write_graph(
        "alpha",
        f"name = 'alpha'\nproject_root = '{dag_home / 'checkout'}'\n"
        "[[nodes]]\nid = 'seed'\n",
    )
    database = await open_database("alpha")
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)
    worktree = WorkTree(
        name="alpha-seed",
        absolute_path="/ws/alpha/seed",
        pr_number=412,
        created_at=STARTED_AT,
    )
    agent = build_agent("token-seed", worktree, [])
    await SqliteNodeAgentRepo(database).save(agent)

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_repo_url.return_value = REPO_URL

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha")

    assert response.json()["nodes"][0]["prUrl"] == f"{REPO_URL}/pull/412"


async def test_dag_detail_returns_is_readable_false_where_the_database_does_not_open(
    mocker: MockerFixture,
    dag_home: Path,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
) -> None:
    write_graph("gamma", "name = 'gamma'\n[[nodes]]\nid = 'y'\n")
    dag_home.joinpath("gamma", "db.sqlite3").write_bytes(b"not a database")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/gamma")

    assert response.status_code == 200
    assert response.json() == {
        "name": "gamma",
        "baseBranch": "",
        "tickIntervalSeconds": 300,
        "nodeCount": 0,
        "nodes": [],
        "lastActivityAt": None,
        "isScheduled": False,
        "isWatching": False,
        "isReadable": False,
        "audit": [],
    }


async def test_dag_detail_returns_the_latest_audit_entries_where_more_exist(
    mocker: MockerFixture,
    build_application: Callable[[CodeRepo], FastAPI],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[SqliteDatabase]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    database = await open_database("alpha")
    audit_entry_repo = SqliteAuditEntryRepo(database)
    for index in range(1, AUDIT_TAIL_SIZE + 2):
        written_at = STARTED_AT + timedelta(minutes=index)
        await audit_entry_repo.save(
            AuditEntry(
                node_id="seed",
                state="pending",
                note=f"pass {index}",
                created_at=written_at,
            )
        )

    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = TestClient(build_application(code_repo)).get("/api/dags/alpha")

    notes = [line["note"] for line in response.json()["audit"]]
    assert notes == [f"pass {index}" for index in range(AUDIT_TAIL_SIZE + 1, 1, -1)]


def test_web_api_exposes_no_route_that_changes_a_dag(
    mocker: MockerFixture, build_application: Callable[[CodeRepo], FastAPI]
) -> None:
    application = build_application(mocker.MagicMock(spec=CodeRepo))

    methods = {
        method
        for route in application.routes
        for method in getattr(route, "methods", set())
    }

    assert methods <= READ_ONLY_METHODS

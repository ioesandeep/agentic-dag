from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_gateway import (
    DagDatabaseGateway,
)
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

STARTED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
WAKE_AT = datetime(2026, 8, 15, 9, 58, tzinfo=UTC)


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
) -> AsyncGenerator[Callable[[str], Awaitable[DagDatabaseGateway]]]:
    opened: list[DagDatabaseGateway] = []

    async def open_for(dag_name: str) -> DagDatabaseGateway:
        db_path = dag_home / dag_name / "db.sqlite3"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        database = SqliteDatabase(engine)
        await database.upgrade_to_head()
        gateway = DagDatabaseGateway(database)
        opened.append(gateway)

        return gateway

    yield open_for

    for gateway in opened:
        await gateway.dispose()


@pytest.fixture
def build_client() -> Callable[[CodeRepo], TestClient]:
    return lambda code_repo: TestClient(
        WebApplicationFactory(
            dag_route=DagRoute(
                DagController(
                    DagWebService(
                        DagService(TomlDagLoader()),
                        DagDatabaseRegistry(),
                        code_repo,
                        {},
                    )
                )
            ),
            health_route=HealthRoute(HealthController()),
        ).build()
    )


async def test_dag_listing_returns_what_a_dag_records_where_its_database_opens(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
) -> None:
    write_graph(
        "alpha",
        "name = 'alpha'\nbase_branch = 'develop'\ntick_interval_seconds = 600\n"
        "[[nodes]]\nid = 'seed'\ntitle = 'seed the table'\nname = 'Leo'\n"
        "[[nodes]]\nid = 'read'\ndepends_on = ['seed']\n",
    )
    gateway = await open_database("alpha")
    await gateway.node_repo.ensure_rows(
        [GraphNode(id="seed", title="seed the table", name="Leo")], STARTED_AT
    )
    await gateway.node_repo.update_state("seed", NodeState.IN_PROGRESS, WAKE_AT)
    await gateway.watcher_repo.save(
        Watcher(dag_name="alpha", pid=4242, started_at=STARTED_AT)
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "alpha",
            "baseBranch": "develop",
            "tickIntervalSeconds": 600,
            "nodeCount": 2,
            "nodes": [
                {
                    "id": "seed",
                    "title": "seed the table",
                    "agentName": "Leo",
                    "state": "in_progress",
                    "dependsOn": [],
                    "updatedAt": "2026-08-15T09:58:00Z",
                },
                {
                    "id": "read",
                    "title": "",
                    "agentName": "read",
                    "state": "pending",
                    "dependsOn": ["seed"],
                    "updatedAt": None,
                },
            ],
            "lastActivityAt": "2026-08-15T09:58:00Z",
            "isScheduled": False,
            "isWatching": True,
            "isReadable": True,
        }
    ]


async def test_dag_listing_returns_is_readable_false_where_the_database_does_not_open(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    dag_home: Path,
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    gateway = await open_database("alpha")
    await gateway.node_repo.ensure_rows([GraphNode(id="seed")], STARTED_AT)
    write_graph("beta", "name = 'beta'\n[[nodes]]\nid = 'x'\n")
    write_graph("gamma", "name = 'gamma'\n[[nodes]]\nid = 'y'\n")
    dag_home.joinpath("gamma", "db.sqlite3").write_bytes(b"not a database")

    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags")

    entries = response.json()
    assert [(entry["name"], entry["isReadable"]) for entry in entries] == [
        ("alpha", True),
        ("beta", False),
        ("gamma", False),
    ]
    assert entries[2] == {
        "name": "gamma",
        "baseBranch": "",
        "tickIntervalSeconds": 300,
        "nodeCount": 0,
        "nodes": [],
        "lastActivityAt": None,
        "isScheduled": False,
        "isWatching": False,
        "isReadable": False,
    }


async def test_dag_listing_returns_a_node_where_only_the_database_records_it(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'seed'\n")
    gateway = await open_database("alpha")
    await gateway.node_repo.ensure_rows(
        [GraphNode(id="PR-42", title="take over #42")], STARTED_AT
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags")

    assert response.json()[0]["nodes"][1] == {
        "id": "PR-42",
        "title": "take over #42",
        "agentName": "take over #42",
        "state": "pending",
        "dependsOn": [],
        "updatedAt": "2026-08-15T09:00:00Z",
    }

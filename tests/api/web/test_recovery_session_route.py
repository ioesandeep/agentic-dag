from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.routes.conversation_route import ConversationRoute
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
from virgo_agentic_dag.api.web.routes.recovery_session_route import (
    RecoverySessionRoute,
)
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
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


@pytest.fixture
def started_at() -> datetime:
    return datetime(2026, 9, 5, 9, 0, tzinfo=UTC)


@pytest.fixture
def ended_at() -> datetime:
    return datetime(2026, 9, 5, 9, 30, tzinfo=UTC)


@pytest.fixture
def dag_home(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root",
        return_value=tmp_path,
    )
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
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
    def build(code_repo: CodeRepo) -> TestClient:
        dag_controller = DagController(
            DagWebService(
                DagService(TomlDagLoader()),
                DagDatabaseRegistry(),
                code_repo,
                {},
                TranscriptPageReader(),
            )
        )
        application = WebApplicationFactory(
            dag_route=DagRoute(dag_controller),
            health_route=HealthRoute(HealthController()),
            memory_route=MemoryRoute(dag_controller),
            conversation_route=ConversationRoute(dag_controller),
            recovery_session_route=RecoverySessionRoute(dag_controller),
        ).build()

        return TestClient(application)

    return build


async def test_recovery_session_route_returns_recovery_session_node_ids_newest_first_when_multiple_recovery_sessions_exist(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
    started_at: datetime,
    ended_at: datetime,
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'API-1'\n")
    gateway = await open_database("alpha")
    closed_recovery_session = RecoverySession(
        session_token="token-1",
        started_at=started_at,
        ended_at=ended_at,
        node_ids='["API-1", "API-2"]',
    )
    await gateway.recovery_session_repo.add(closed_recovery_session)

    open_recovery_session = RecoverySession(
        session_token="token-2", started_at=ended_at, node_ids='["API-3"]'
    )
    await gateway.recovery_session_repo.add(open_recovery_session)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags/alpha/recovery-sessions")

    assert [recovery_session["nodeIds"] for recovery_session in response.json()] == [
        ["API-3"],
        ["API-1", "API-2"],
    ]


async def test_recovery_session_route_responds_200_with_an_empty_list_when_no_recovery_sessions_exist(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'API-1'\n")
    await open_database("alpha")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags/alpha/recovery-sessions")

    assert response.status_code == 200
    assert response.json() == []


def test_recovery_session_route_responds_404_when_no_dag_has_the_name(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'API-1'\n")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags/ghost/recovery-sessions")

    assert response.status_code == 404
    assert response.json() == {"detail": "no dag named ghost lives on this host"}


async def test_recovery_session_route_matches_before_the_node_route_when_a_node_identifier_matches_the_route_suffix(
    mocker: MockerFixture,
    build_client: Callable[[CodeRepo], TestClient],
    write_graph: Callable[[str, str], None],
    open_database: Callable[[str], Awaitable[DagDatabaseGateway]],
) -> None:
    write_graph("alpha", "name = 'alpha'\n[[nodes]]\nid = 'recovery-sessions'\n")
    await open_database("alpha")
    code_repo = mocker.MagicMock(spec=CodeRepo)

    response = build_client(code_repo).get("/api/dags/alpha/recovery-sessions")

    assert response.json() == []

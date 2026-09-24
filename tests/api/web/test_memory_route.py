import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.routes.conversation_route import ConversationRoute
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

UPDATED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
MEMORY_PATH = "/api/dags/alpha/memory"


@pytest.fixture
def dag_home(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root",
        return_value=tmp_path,
    )
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    return tmp_path


@pytest.fixture
def write_graph(dag_home: Path) -> Callable[[str], None]:
    def write(node_id: str) -> None:
        home = dag_home / "alpha"
        home.mkdir(parents=True, exist_ok=True)
        home.joinpath("dag.toml").write_text(
            f"name = 'alpha'\n[[nodes]]\nid = '{node_id}'\n", encoding="utf-8"
        )

    return write


@pytest.fixture
def client(mocker: MockerFixture, dag_home: Path) -> TestClient:
    dag_controller = DagController(
        DagWebService(
            DagService(TomlDagLoader()),
            DagDatabaseRegistry(),
            mocker.MagicMock(spec=CodeRepo),
            {},
            TranscriptPageReader(),
        )
    )
    application = WebApplicationFactory(
        dag_route=DagRoute(dag_controller),
        health_route=HealthRoute(HealthController()),
        memory_route=MemoryRoute(dag_controller),
        conversation_route=ConversationRoute(dag_controller),
    ).build()

    return TestClient(application)


def test_memory_returns_the_file_text_and_modification_time_when_the_file_exists(
    client: TestClient, dag_home: Path, write_graph: Callable[[str], None]
) -> None:
    write_graph("seed")
    memory_file = dag_home / "alpha" / "memory.md"
    memory_file.write_text("- rebase before the push\n", encoding="utf-8")
    os.utime(memory_file, (UPDATED_AT.timestamp(), UPDATED_AT.timestamp()))

    response = client.get(MEMORY_PATH)

    assert response.json()["content"] == "- rebase before the push\n"
    assert response.json()["updatedAt"] == "2026-08-15T09:00:00Z"


def test_memory_returns_empty_content_and_a_null_time_when_the_file_does_not_exist(
    client: TestClient, write_graph: Callable[[str], None]
) -> None:
    write_graph("seed")

    response = client.get(MEMORY_PATH)

    assert response.json()["content"] == ""
    assert response.json()["updatedAt"] is None


def test_memory_endpoint_returns_a_memory_response_when_a_node_id_is_memory(
    client: TestClient, write_graph: Callable[[str], None]
) -> None:
    write_graph("memory")

    response = client.get(MEMORY_PATH)

    assert response.status_code == 200
    assert set(response.json()) == {"content", "updatedAt"}

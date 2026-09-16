import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e


def test_health_route_responds_ok_where_the_server_is_up(mocker: MockerFixture) -> None:
    code_repo = mocker.MagicMock(spec=CodeRepo)
    dag_controller = DagController(
        DagWebService(DagService(TomlDagLoader()), DagDatabaseRegistry(), code_repo, {})
    )
    factory = WebApplicationFactory(
        dag_route=DagRoute(dag_controller),
        health_route=HealthRoute(HealthController()),
    )
    client = TestClient(factory.build())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

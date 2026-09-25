import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
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
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e


def test_health_route_responds_ok_where_the_server_is_up(mocker: MockerFixture) -> None:
    code_repo = mocker.MagicMock(spec=CodeRepo)
    dag_controller = DagController(
        DagWebService(
            DagService(TomlDagLoader()),
            DagDatabaseRegistry(),
            code_repo,
            {},
            TranscriptPageReader(),
        )
    )
    node_action_controller = NodeActionController(
        mocker.MagicMock(spec=NodeActionService)
    )
    factory = WebApplicationFactory(
        dag_route=DagRoute(dag_controller),
        health_route=HealthRoute(HealthController()),
        memory_route=MemoryRoute(dag_controller),
        conversation_route=ConversationRoute(dag_controller),
        node_action_route=NodeActionRoute(node_action_controller),
        recovery_session_route=RecoverySessionRoute(dag_controller),
    )
    client = TestClient(factory.build())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

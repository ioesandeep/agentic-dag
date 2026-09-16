import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.tick_command_handler import TickCommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.graph_validation_service import (
    GraphValidationService,
)
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.domain.validation.validation_result import ValidationResult
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.learning.learning_dispatch_service import (
    LearningDispatchService,
)
from virgo_agentic_dag.services.node_state_handlers.node_state_handling_facade import (
    NodeStateHandlingFacade,
)
from virgo_agentic_dag.services.recovery.recovery_dispatch_service import (
    RecoveryDispatchService,
)
from virgo_agentic_dag.services.recovery.recovery_scan_service import (
    RecoveryScanService,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 6, tzinfo=UTC)


@pytest.fixture
def resting_node() -> Node:
    return Node(
        id="A",
        state=NodeState.RESTING.value,
        created_at=NOW,
        updated_at=NOW,
        recovery_attempts_allowed=1,
    )


async def test_tick_dispatches_a_recovery_session_when_a_node_fails(
    mocker: MockerFixture, tmp_path: Path, resting_node: Node
) -> None:
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = Graph(
        name="demo", nodes=[GraphNode(id="A")]
    )

    validation_service = mocker.MagicMock(spec=GraphValidationService)
    validation_service.validate_graph.return_value = ValidationResult()

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [resting_node]

    recovery_scan_service = mocker.MagicMock(spec=RecoveryScanService)
    recovery_scan_service.get_recoverable_nodes.return_value = [resting_node]
    recovery_dispatch_service = mocker.MagicMock(spec=RecoveryDispatchService)
    recovery_dispatch_service.dispatch.return_value = TickResponse(sessions_started=1)

    learning_dispatch_service = mocker.MagicMock(spec=LearningDispatchService)
    learning_dispatch_service.dispatch.return_value = TickResponse()

    node_state_handling_facade = mocker.MagicMock(spec=NodeStateHandlingFacade)
    node_state_handling_facade.handle_in_progress_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_resting_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_pending_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_merged_nodes.return_value = TickResponse()

    out = io.StringIO()
    handler = TickCommandHandler(
        graph_builder=graph_builder,
        validation_service=validation_service,
        node_repo=node_repo,
        node_state_handling_facade=node_state_handling_facade,
        recovery_scan_service=recovery_scan_service,
        recovery_dispatch_service=recovery_dispatch_service,
        learning_dispatch_service=learning_dispatch_service,
        out=out,
    )

    exit_code = await handler.handle(TickCommand(dag_path=tmp_path / "dag.toml"))

    dispatched_nodes = recovery_dispatch_service.dispatch.await_args.args[0]
    assert exit_code is ExitCode.SUCCESS
    assert dispatched_nodes == [resting_node]
    assert out.getvalue() == "applied 0 events, started 1 sessions\n"


async def test_tick_dispatches_no_recovery_session_when_no_node_fails(
    mocker: MockerFixture, tmp_path: Path, resting_node: Node
) -> None:
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = Graph(
        name="demo", nodes=[GraphNode(id="A")]
    )

    validation_service = mocker.MagicMock(spec=GraphValidationService)
    validation_service.validate_graph.return_value = ValidationResult()

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [resting_node]

    recovery_scan_service = mocker.MagicMock(spec=RecoveryScanService)
    recovery_scan_service.get_recoverable_nodes.return_value = []
    recovery_dispatch_service = mocker.MagicMock(spec=RecoveryDispatchService)
    recovery_dispatch_service.dispatch.return_value = TickResponse()

    learning_dispatch_service = mocker.MagicMock(spec=LearningDispatchService)
    learning_dispatch_service.dispatch.return_value = TickResponse()

    node_state_handling_facade = mocker.MagicMock(spec=NodeStateHandlingFacade)
    node_state_handling_facade.handle_in_progress_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_resting_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_pending_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_merged_nodes.return_value = TickResponse()

    out = io.StringIO()
    handler = TickCommandHandler(
        graph_builder=graph_builder,
        validation_service=validation_service,
        node_repo=node_repo,
        node_state_handling_facade=node_state_handling_facade,
        recovery_scan_service=recovery_scan_service,
        recovery_dispatch_service=recovery_dispatch_service,
        learning_dispatch_service=learning_dispatch_service,
        out=out,
    )

    exit_code = await handler.handle(TickCommand(dag_path=tmp_path / "dag.toml"))

    dispatched_nodes = recovery_dispatch_service.dispatch.await_args.args[0]
    assert exit_code is ExitCode.SUCCESS
    assert dispatched_nodes == []
    assert out.getvalue() == "applied 0 events, started 0 sessions\n"


async def test_tick_reports_one_learning_session_as_started_when_a_settled_node_is_due(
    mocker: MockerFixture, tmp_path: Path, resting_node: Node
) -> None:
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = Graph(
        name="demo", nodes=[GraphNode(id="A")]
    )

    validation_service = mocker.MagicMock(spec=GraphValidationService)
    validation_service.validate_graph.return_value = ValidationResult()

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [resting_node]

    recovery_scan_service = mocker.MagicMock(spec=RecoveryScanService)
    recovery_scan_service.get_recoverable_nodes.return_value = []
    recovery_dispatch_service = mocker.MagicMock(spec=RecoveryDispatchService)
    recovery_dispatch_service.dispatch.return_value = TickResponse()

    learning_dispatch_service = mocker.MagicMock(spec=LearningDispatchService)
    learning_dispatch_service.dispatch.return_value = TickResponse(sessions_started=1)

    node_state_handling_facade = mocker.MagicMock(spec=NodeStateHandlingFacade)
    node_state_handling_facade.handle_in_progress_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_resting_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_pending_nodes.return_value = TickResponse()
    node_state_handling_facade.handle_merged_nodes.return_value = TickResponse()

    out = io.StringIO()
    handler = TickCommandHandler(
        graph_builder=graph_builder,
        validation_service=validation_service,
        node_repo=node_repo,
        node_state_handling_facade=node_state_handling_facade,
        recovery_scan_service=recovery_scan_service,
        recovery_dispatch_service=recovery_dispatch_service,
        learning_dispatch_service=learning_dispatch_service,
        out=out,
    )

    exit_code = await handler.handle(TickCommand(dag_path=tmp_path / "dag.toml"))

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == "applied 0 events, started 1 sessions\n"

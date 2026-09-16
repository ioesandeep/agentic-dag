"""Advances a run by one control pass over the nodes of its graph."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TextIO

from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.graph_service import GraphService
from virgo_agentic_dag.domain.service.graph_validation_service import (
    GraphValidationService,
)
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
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
from virgo_agentic_dag.utils.format_label import format_label


class TickCommandHandler(CommandHandler[TickCommand]):
    """Advances a run by one pass, one state at a time, reading fresh rows before each."""

    def __init__(
        self,
        graph_builder: GraphBuilder,
        validation_service: GraphValidationService,
        node_repo: NodeRepo,
        node_state_handling_facade: NodeStateHandlingFacade,
        recovery_scan_service: RecoveryScanService,
        recovery_dispatch_service: RecoveryDispatchService,
        learning_dispatch_service: LearningDispatchService,
        out: TextIO,
    ) -> None:
        self._graph_builder = graph_builder
        self.validation_service = validation_service
        self.node_repo = node_repo
        self._node_state_handling_facade = node_state_handling_facade
        self._recovery_scan_service = recovery_scan_service
        self._recovery_dispatch_service = recovery_dispatch_service
        self._learning_dispatch_service = learning_dispatch_service
        self._out = out

    async def handle(self, command: TickCommand) -> ExitCode:
        graph = self._graph_builder.build_from_path(command.dag_path)
        result = self.validation_service.validate_graph(graph)
        findings = result.describe()

        self._out.write(findings)
        if result.is_blocking():
            return ExitCode.FAILURE

        current_time = datetime.now(UTC)
        await self.node_repo.ensure_rows(graph.nodes, current_time)

        tick_response = TickResponse()

        in_progress_response = (
            await self._node_state_handling_facade.handle_in_progress_nodes(
                graph, current_time
            )
        )
        tick_response = tick_response.increment_with(in_progress_response)

        resting_response = await self._node_state_handling_facade.handle_resting_nodes(
            graph, current_time
        )
        tick_response = tick_response.increment_with(resting_response)

        pending_response = await self._node_state_handling_facade.handle_pending_nodes(
            graph, current_time
        )
        tick_response = tick_response.increment_with(pending_response)

        merged_response = await self._node_state_handling_facade.handle_merged_nodes(
            graph, current_time
        )
        tick_response = tick_response.increment_with(merged_response)

        recovery_response, learning_response = await asyncio.gather(
            self._recover_failed_nodes(current_time),
            self._learning_dispatch_service.dispatch(current_time),
        )
        tick_response = tick_response.increment_with(recovery_response)
        tick_response = tick_response.increment_with(learning_response)

        nodes = await self.node_repo.get_all()
        graph_service = GraphService(graph)
        if graph_service.is_complete(nodes):
            self._out.write(LABELS["runComplete"])

            return ExitCode.RUN_COMPLETE

        summary = format_label(
            LABELS["tickOutcome"],
            {
                "events": tick_response.events_applied,
                "sessions": tick_response.sessions_started,
            },
        )
        self._out.write(summary)

        return ExitCode.SUCCESS

    async def _recover_failed_nodes(self, current_time: datetime) -> TickResponse:
        recoverable_nodes = await self._recovery_scan_service.get_recoverable_nodes(
            current_time
        )

        return await self._recovery_dispatch_service.dispatch(
            recoverable_nodes, current_time
        )

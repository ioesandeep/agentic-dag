"""Runs the `preview` command, printing the graph as a diagram with its agent count."""

from __future__ import annotations

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.preview_command import PreviewCommand
from virgo_agentic_dag.domain.preview.renderer import Renderer
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class PreviewCommandHandler(CommandHandler[PreviewCommand]):
    """Shows the graph as a diagram and how many agents a run of it would start."""

    def __init__(self, dag_spec: DagSpec, renderer: Renderer) -> None:
        self._dag_spec = dag_spec
        self._renderer = renderer

    async def handle(self, command: PreviewCommand) -> ExitCode:
        agents = len(self._dag_spec.nodes)

        emit(self._renderer.render(self._dag_spec))
        emit(format_label(LABELS["previewAgentCount"], {"agents": agents}))

        return ExitCode.SUCCESS

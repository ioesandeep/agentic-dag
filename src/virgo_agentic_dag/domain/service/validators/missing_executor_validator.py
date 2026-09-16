"""Finds nodes that resolve to no executor agent."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class MissingExecutorValidator(GraphValidator):
    """Reports every node that resolves to no executor agent."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        return [
            ValidationError(
                code="missing-executor",
                message=format_label(LABELS["missingExecutor"], {"node_id": node.id}),
                node_id=node.id,
            )
            for node in graph.nodes
            if node.executor_agent is None
        ]

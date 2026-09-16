"""Finds edges that point at nodes the graph never declares."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class MissingDependencyValidator(GraphValidator):
    """Reports every dependency on a node that is not in the graph."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        known = {node.id for node in graph.nodes}

        return [
            ValidationError(
                code="unknown-dependency",
                message=format_label(
                    LABELS["unknownDependency"], {"node_id": node.id, "dep_id": dep_id}
                ),
                node_id=node.id,
            )
            for node in graph.nodes
            for dep_id in node.depends_on
            if dep_id not in known
        ]

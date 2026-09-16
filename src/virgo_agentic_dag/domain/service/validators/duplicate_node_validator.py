"""Finds node ids the graph declares more than once."""

from __future__ import annotations

from collections import Counter

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class DuplicateNodeValidator(GraphValidator):
    """Reports every node id that appears more than once."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        return [
            ValidationError(
                code="duplicate-node",
                message=format_label(LABELS["duplicateNode"], {"node_id": node_id}),
                node_id=node_id,
            )
            for node_id in self._find_duplicated_ids(graph)
        ]

    def _find_duplicated_ids(self, graph: Graph) -> list[str]:
        counts = Counter(node.id for node in graph.nodes)

        return [node_id for node_id, count in counts.items() if count > 1]

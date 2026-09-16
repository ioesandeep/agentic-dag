"""Finds dependency cycles, which no execution order could ever satisfy."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class CycleValidator(GraphValidator):
    """Reports the nodes remaining after topological elimination, which form a cycle."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        cycle_members = self._find_cycle_members(graph)
        if not cycle_members:
            return []

        return [
            ValidationError(
                code="dependency-cycle",
                message=format_label(
                    LABELS["dependencyCycle"],
                    {"node_ids": ", ".join(sorted(cycle_members))},
                ),
            )
        ]

    def _find_cycle_members(self, graph: Graph) -> set[str]:
        known = {node.id for node in graph.nodes}
        remaining = {
            node.id: {dep for dep in node.depends_on if dep in known}
            for node in graph.nodes
        }
        peeled = True
        while peeled:
            startable = {node_id for node_id, deps in remaining.items() if not deps}
            peeled = bool(startable)
            for node_id in startable:
                del remaining[node_id]

            for deps in remaining.values():
                deps.difference_update(startable)

        return set(remaining)

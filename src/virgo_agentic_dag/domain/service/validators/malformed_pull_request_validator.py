"""Finds nodes whose declared pull request is not a readable url."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

_URL_SCHEMES = ("http://", "https://")


class MalformedPullRequestValidator(GraphValidator):
    """Reports every node whose pull request is not an http url."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        return [
            ValidationError(
                code="pr-not-url",
                message=format_label(
                    LABELS["nodePrNotUrl"], {"node_id": node.id, "pr": node.pr}
                ),
                node_id=node.id,
            )
            for node in graph.nodes
            if node.pr and not node.pr.startswith(_URL_SCHEMES)
        ]

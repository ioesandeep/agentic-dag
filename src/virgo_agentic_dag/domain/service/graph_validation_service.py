"""Runs every graph rule and gathers what they found into one result."""

from __future__ import annotations

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.domain.validation.validation_result import ValidationResult


class GraphValidationService:
    """Applies each validator in order and returns everything they reported."""

    def __init__(self, graph_validators: list[GraphValidator]) -> None:
        self._graph_validators = graph_validators

    def validate_graph(self, graph: Graph) -> ValidationResult:
        """Return every finding from every rule, blocking or not."""
        errors: list[ValidationError] = []
        for validator in self._graph_validators:
            errors.extend(validator.validate(graph))

        return ValidationResult(errors=errors)

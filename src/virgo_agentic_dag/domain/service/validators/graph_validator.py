"""One rule a graph must satisfy before the controller will run it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.validation.validation_error import ValidationError


class GraphValidator(ABC):
    """Checks one property of a graph and reports every place it does not hold."""

    @abstractmethod
    def validate(self, graph: Graph) -> list[ValidationError]:
        """Return every finding this rule makes about the graph."""

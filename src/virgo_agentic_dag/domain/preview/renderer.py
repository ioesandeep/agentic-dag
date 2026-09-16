"""The interface that turns a graph into text a person reads before a run starts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.specs.dag_spec import DagSpec


class Renderer(ABC):
    """Renders a graph as the text a person reads to decide whether to start it."""

    @abstractmethod
    def render(self, spec: DagSpec) -> str:
        """Return the graph as text in this renderer's notation."""

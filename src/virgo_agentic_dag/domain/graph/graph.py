"""The executable graph of a run, holding its task name and ordered nodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from virgo_agentic_dag.domain.graph.graph_node import GraphNode


@dataclass(frozen=True)
class Graph:
    # name of the task this graph carries out
    name: str
    nodes: list[GraphNode]
    project_root: Path | None = None

"""Builds the domain Graph from an approved graph file, whatever format holds it."""

from __future__ import annotations

from pathlib import Path

from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec


class GraphBuilder:
    """Turns a graph file into the Graph everything downstream works on."""

    def __init__(self, dag_loader: DagLoader) -> None:
        self._dag_loader = dag_loader

    def build_from_path(self, dag_path: Path) -> Graph:
        """Load the file at this path and return it as the domain graph."""
        spec = self._dag_loader.load(dag_path)

        return self.create_graph(spec)

    def create_graph(self, dag_spec: DagSpec) -> Graph:
        """Return a graph created from the DAG specification."""
        graph_nodes = [
            self._build_node(dag_spec, node_spec) for node_spec in dag_spec.nodes
        ]

        return Graph(name=dag_spec.name, nodes=graph_nodes)

    def _build_node(self, dag_spec: DagSpec, spec: NodeSpec) -> GraphNode:
        return GraphNode(
            id=spec.id,
            title=spec.title,
            name=spec.name,
            instructions=spec.instructions,
            depends_on=spec.depends_on,
            executor_agent=dag_spec.get_executor_agent(spec),
            project_root=dag_spec.get_project_root(spec),
            workspace_path=dag_spec.get_workspace_path(spec),
            base_branch=dag_spec.get_base_branch(spec),
            cooldown_seconds=dag_spec.get_cooldown_seconds(spec),
            pr=spec.pr,
            recovery_attempts_allowed=dag_spec.caps.node_recoveries,
        )

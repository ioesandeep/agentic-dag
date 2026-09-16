"""Renders a graph as a Mermaid flowchart, the notation a preview prints today."""

from __future__ import annotations

from virgo_agentic_dag.domain.preview.renderer import Renderer
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec


class MermaidRenderer(Renderer):
    """Renders a DagSpec as a Mermaid flowchart of nodes and dependency edges."""

    def render(self, spec: DagSpec) -> str:
        lines = ["flowchart TD"]
        for node in spec.nodes:
            lines.append(f"    {node.id}{self._render_label(node)}")

        for node in spec.nodes:
            for dep in node.depends_on:
                lines.append(f"    {dep} --> {node.id}")

        return "\n".join(lines)

    def _render_label(self, node: NodeSpec) -> str:
        """Return the node's Mermaid label, marking a takeover so it reads as one."""
        if node.is_adopted():
            return f'["{node.id} (adopted)"]'

        return f"[{node.id}]"

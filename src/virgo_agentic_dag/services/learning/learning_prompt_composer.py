"""Learning prompt composition for nodes with pull requests."""

from __future__ import annotations

from pathlib import Path

from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.dag_utils import get_runbook_text
from virgo_agentic_dag.utils.format_label import format_label


class LearningPromptComposer:
    """A composer for learning prompts about nodes with pull requests."""

    def __init__(self, learnings_path: Path, repo_slug: str) -> None:
        self._learnings_path = learnings_path
        self._repo_slug = repo_slug

    def compose_prompt(self, nodes: list[Node]) -> str:
        """Returns a learning prompt for nodes with pull requests."""
        node_sections: list[str] = []
        for node in nodes:
            node_section = self._compose_node_section(node)
            if node_section is not None:
                node_sections.append(node_section)

        batch = "\n".join(node_sections)
        module_file = Path(__file__)
        runbook = get_runbook_text(module_file, "learning_runbook.md")
        values = {
            "learnings_path": self._learnings_path,
            "repo_slug": self._repo_slug,
            "runbook": runbook,
            "batch": batch,
        }

        return format_label(LABELS["learningPrompt"], values)

    def _compose_node_section(self, node: Node) -> str | None:
        pr_number = node.get_pr_number()
        if pr_number is None:
            return None

        values = {
            "node_id": node.id,
            "title": node.title,
            "state": node.state,
            "pr_number": pr_number,
        }

        return format_label(LABELS["learningBatchNode"], values)

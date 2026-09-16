"""Composes the prompt a recovery agent session starts with."""

from __future__ import annotations

from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path

from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

MISSING_VALUE = LABELS["recoveryValueMissing"]


class RecoveryPromptComposer:
    """Composes the prompt for a batch of failed nodes, with every value from a node quoted as evidence."""

    def __init__(
        self,
        node_recovery_repo: NodeRecoveryRepo,
        dag_path: Path,
        dagctl_path: Path,
        transcript_locators: Mapping[ExecutorAgent, TranscriptLocator],
    ) -> None:
        self._node_recovery_repo = node_recovery_repo
        self._dag_path = dag_path
        self._dagctl_path = dagctl_path
        self._transcript_locators = transcript_locators

    async def compose_prompt(self, nodes: list[Node]) -> str:
        """Return the prompt for this batch of failed nodes."""
        node_sections: list[str] = []
        for node in nodes:
            attempt_count = await self._node_recovery_repo.count_by_node_id(node.id)
            node_section = self._compose_node_section(node, attempt_count)
            node_sections.append(node_section)

        batch = "\n".join(node_sections)
        runbook = (files() / "recovery_runbook.md").read_text(encoding="utf-8")
        values = {
            "dagctl_path": self._dagctl_path,
            "dag_path": self._dag_path,
            "runbook": runbook,
            "batch": batch,
        }

        return format_label(LABELS["recoveryPrompt"], values)

    def _compose_node_section(self, node: Node, attempt_count: int) -> str:
        agent = node.agent
        worktree = agent.worktree if agent is not None else None
        transcript_path = self._get_transcript_path(agent)
        latest_session = node.get_latest_session()
        values = {
            "node_id": node.id,
            "state": node.state,
            "transcript_path": transcript_path or MISSING_VALUE,
            "attempt_count": attempt_count,
            **self._get_worktree_values(worktree),
            **self._get_session_values(latest_session),
        }

        return format_label(LABELS["recoveryBatchNode"], values)

    def _get_transcript_path(self, agent: NodeAgent | None) -> Path | None:
        if agent is None:
            return None

        transcript_locator = self._transcript_locators[ExecutorAgent(agent.name)]

        return transcript_locator.get_transcript_path(agent)

    def _get_worktree_values(self, worktree: WorkTree | None) -> dict[str, str]:
        if worktree is None:
            return {
                "worktree_path": MISSING_VALUE,
                "branch": MISSING_VALUE,
                "pr_number": MISSING_VALUE,
                "log_path": MISSING_VALUE,
            }

        pr_number = f"#{worktree.pr_number}" if worktree.pr_number else MISSING_VALUE

        return {
            "worktree_path": worktree.absolute_path,
            "branch": worktree.branch or MISSING_VALUE,
            "pr_number": pr_number,
            "log_path": str(worktree.get_log_path()),
        }

    def _get_session_values(
        self, latest_session: AgentSession | None
    ) -> dict[str, str]:
        if latest_session is None:
            return {"exit_code": MISSING_VALUE, "log_tail": MISSING_VALUE}

        exit_code = latest_session.exit_code
        exit_code_text = MISSING_VALUE if exit_code is None else str(exit_code)

        return {
            "exit_code": exit_code_text,
            "log_tail": latest_session.log_tail or MISSING_VALUE,
        }

"""Prints one node's current row for the recovery agent to decide from."""

from __future__ import annotations

from collections.abc import Mapping

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.examine_command import ExamineCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class NodeExaminationService:
    """Reports the node, worktree, session and recovery rows a recovery decision needs."""

    def __init__(
        self,
        node_repo: NodeRepo,
        node_recovery_repo: NodeRecoveryRepo,
        transcript_locators: Mapping[ExecutorAgent, TranscriptLocator],
    ) -> None:
        self._node_repo = node_repo
        self._node_recovery_repo = node_recovery_repo
        self._transcript_locators = transcript_locators

    async def examine(self, command: ExamineCommand) -> ExitCode:
        """Print this node's row as the store has it now, refusing an id the run does not have."""
        node = await self._node_repo.read(command.node_id)
        if node is None:
            emit(format_label(LABELS["nodeNotInRun"], {"node_id": command.node_id}))

            return ExitCode.FAILURE

        self._report_node(node)
        self._report_worktree(node)
        self._report_session(node)
        await self._report_recovery(node)

        return ExitCode.SUCCESS

    def _report_node(self, node: Node) -> None:
        values = {
            "node_id": node.id,
            "state": node.state,
            "updated_at": node.updated_at,
        }
        emit(format_label(LABELS["examineNode"], values))

    def _report_worktree(self, node: Node) -> None:
        worktree = node.agent.worktree if node.agent is not None else None
        if worktree is None:
            emit(LABELS["examineNoWorktree"])

            return

        worktree_values = self._get_worktree_values(worktree)
        emit(format_label(LABELS["examineWorktree"], worktree_values))

    def _get_worktree_values(self, worktree: WorkTree) -> dict[str, object]:
        return {
            "path": worktree.absolute_path,
            "exists": worktree.exists_on_disk(),
            "reclaimed": worktree.is_reclaimed(),
            "branch": worktree.branch or LABELS["recoveryValueMissing"],
            "pr_number": worktree.pr_number or LABELS["recoveryValueMissing"],
        }

    def _report_session(self, node: Node) -> None:
        agent = node.agent
        latest_session = node.get_latest_session()
        if agent is None or latest_session is None:
            emit(LABELS["examineNoSession"])

            return

        session_values = self._get_session_values(latest_session)
        emit(format_label(LABELS["examineSession"], session_values))

        overdue_count = agent.count_overdue_sessions()
        emit(format_label(LABELS["examineOverdue"], {"count": overdue_count}))

        transcript_locator = self._transcript_locators[ExecutorAgent(agent.name)]
        transcript_path = transcript_locator.get_transcript_path(agent)
        transcript = transcript_path or LABELS["recoveryValueMissing"]
        emit(format_label(LABELS["examineTranscript"], {"path": transcript}))

        log_tail = latest_session.log_tail or LABELS["recoveryValueMissing"]
        emit(format_label(LABELS["examineLogTail"], {"log_tail": log_tail}))

    def _get_session_values(self, session: AgentSession) -> dict[str, object]:
        missing = LABELS["recoveryValueMissing"]
        exit_code = missing if session.exit_code is None else session.exit_code

        return {
            "session_id": session.id,
            "trigger": session.triggered_by,
            "ended_at": session.ended_at or missing,
            "end_state": session.end_state or missing,
            "exit_code": exit_code,
            "alive": session.is_process_alive(),
        }

    async def _report_recovery(self, node: Node) -> None:
        row_count = await self._node_recovery_repo.count_by_node_id(node.id)
        values = {
            "attempts_left": node.recovery_attempts_allowed,
            "row_count": row_count,
        }
        emit(format_label(LABELS["examineAttempts"], values))

        newest_recovery = await self._node_recovery_repo.get_newest_recovery_by_node_id(
            node.id
        )
        if newest_recovery is None:
            return

        recovery_values = self._get_recovery_values(newest_recovery)
        emit(format_label(LABELS["examineRecovery"], recovery_values))

    def _get_recovery_values(self, recovery: NodeRecovery) -> dict[str, object]:
        return {
            "cause": recovery.cause,
            "recoverable": recovery.recoverable,
            "recover_at": recovery.recover_at,
            "action": recovery.action,
        }

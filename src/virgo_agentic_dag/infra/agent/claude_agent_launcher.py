"""The AgentLauncher that runs a node's work as a detached Claude Code process."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label
from virgo_agentic_dag.utils.process import is_process_alive

logger = logging.getLogger(__name__)

# TODO: make the model configurable per run rather than pinned here.
_AGENT_FLAGS: tuple[str, ...] = (
    "-p",
    "--permission-mode",
    "bypassPermissions",
    "--model",
    "claude-opus-5-5",
    "--effort",
    "max",
)
_SHELL = "sh"
_RECORD_EXIT_CODE_SCRIPT = 'exit_path="$1"; shift; "$@"; echo "$?" > "$exit_path"'


class ClaudeAgentLauncher(AgentLauncher):
    """Runs a node's executions as detached claude processes, one resumable
    conversation per node."""

    _BINARY = "claude"

    def __init__(
        self, timeout_seconds: int, max_turns: int, learnings_path: Path
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_turns = max_turns
        self._learnings_path = learnings_path

    async def launch(
        self, graph_node: GraphNode, brief: str, agent: NodeAgent
    ) -> AgentSession:
        worktree = self._require_worktree(agent)
        argv = self._build_launch_argv(brief, agent.resume_token)
        started = datetime.now(UTC)
        pid = await asyncio.to_thread(self._spawn, argv, worktree)

        return AgentSession(
            agent_id=agent.id, started_at=started, triggered_by="launch", pid=pid
        )

    async def wake(
        self, graph_node: GraphNode, news: str, agent: NodeAgent
    ) -> AgentSession:
        worktree = self._require_worktree(agent)
        argv = self._build_wake_argv(news, agent.resume_token)
        started = datetime.now(UTC)
        pid = await asyncio.to_thread(self._spawn, argv, worktree)

        return AgentSession(
            agent_id=agent.id,
            started_at=started,
            triggered_by="wake",
            pid=pid,
            marks_before=worktree.marks,
        )

    async def supervise(self, session: AgentSession) -> SessionStatus:
        if session.pid is None or not is_process_alive(session.pid):
            return SessionStatus.FINISHED

        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)

        deadline = started_at + timedelta(seconds=self._timeout_seconds)
        if datetime.now(UTC) > deadline:
            return SessionStatus.OVERDUE

        return SessionStatus.ALIVE

    async def stop(self, session: AgentSession) -> None:
        if session.pid is None:
            return

        try:
            os.killpg(session.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return

    def _require_worktree(self, agent: NodeAgent) -> WorkTree:
        if agent.worktree is None:
            raise WorktreeError(f"agent {agent.id} has no worktree to run in")

        return agent.worktree

    def _build_launch_argv(self, brief: str, resume_token: str) -> tuple[str, ...]:
        turns = self._build_turns()
        prompt = self._get_prompt_with_learnings(brief)

        return (
            self._BINARY,
            *_AGENT_FLAGS,
            "--session-id",
            resume_token,
            *turns,
            prompt,
        )

    def _build_wake_argv(self, news: str, resume_token: str) -> tuple[str, ...]:
        turns = self._build_turns()
        prompt = self._get_prompt_with_learnings(news)

        return (
            self._BINARY,
            *_AGENT_FLAGS,
            "--resume",
            resume_token,
            *turns,
            prompt,
        )

    def _build_turns(self) -> tuple[str, ...]:
        return ("--max-turns", str(self._max_turns))

    def _get_prompt_with_learnings(self, prompt: str) -> str:
        learnings = self._get_learnings()
        if not learnings:
            return prompt

        learnings_section = format_label(
            LABELS["runLearnings"], {"learnings": learnings}
        )

        return prompt + learnings_section

    def _get_learnings(self) -> str:
        try:
            return self._learnings_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""
        except OSError as error:
            logger.warning("%s did not open: %s", self._learnings_path, error)

            return ""

    def _spawn(self, argv: tuple[str, ...], worktree: WorkTree) -> int:
        log_path = worktree.get_log_path()
        exit_path = worktree.get_exit_path()
        exit_path.unlink(missing_ok=True)
        wrapped_argv = [
            _SHELL,
            "-c",
            _RECORD_EXIT_CODE_SCRIPT,
            _SHELL,
            str(exit_path),
            *argv,
        ]
        with open(log_path, "w") as log:
            process = subprocess.Popen(
                wrapped_argv,
                cwd=worktree.absolute_path,
                env=dict(os.environ),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        return process.pid

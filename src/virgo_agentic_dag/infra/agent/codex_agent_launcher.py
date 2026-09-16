"""The AgentLauncher that runs a node's work as a detached Codex process."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label
from virgo_agentic_dag.utils.process import is_process_alive

logger = logging.getLogger(__name__)


class CodexAgentLauncher(AgentLauncher):
    """Runs a node's executions as detached codex processes, one resumable
    thread per node."""

    _BINARY = "codex"
    _AGENT_FLAGS: tuple[str, ...] = (
        "--json",
        "--skip-git-repo-check",
        "-c",
        'sandbox_mode="workspace-write"',
        "-c",
        'approval_policy="on-request"',
        "-c",
        'approvals_reviewer="auto_review"',
    )
    _SESSION_RUNNER = Path(__file__).with_name("codex_session_runner.py")

    def __init__(
        self,
        timeout_seconds: int,
        learnings_path: Path,
        transcript_locator: TranscriptLocator,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._learnings_path = learnings_path
        self._transcript_locator = transcript_locator

    async def launch(
        self, graph_node: GraphNode, brief: str, agent: NodeAgent
    ) -> AgentSession:
        """Start a Codex conversation with the node's instructions."""
        prompt = await asyncio.to_thread(self._get_prompt_with_learnings, brief)
        argv = [self._BINARY, "exec", *self._AGENT_FLAGS, prompt]
        started_at = datetime.now(UTC)
        pid = await asyncio.to_thread(self._spawn, argv, agent)

        return AgentSession(
            agent_id=agent.id, started_at=started_at, triggered_by="launch", pid=pid
        )

    async def wake(
        self, graph_node: GraphNode, news: str, agent: NodeAgent
    ) -> AgentSession:
        """Resume the node's Codex conversation with new work."""
        resume_id = await asyncio.to_thread(self._get_resume_id, agent)
        prompt = await asyncio.to_thread(self._get_prompt_with_learnings, news)
        argv = [self._BINARY, "exec", "resume", *self._AGENT_FLAGS, resume_id, prompt]
        started_at = datetime.now(UTC)
        pid = await asyncio.to_thread(self._spawn, argv, agent)

        return AgentSession(
            agent_id=agent.id,
            started_at=started_at,
            triggered_by="wake",
            pid=pid,
            marks_before=agent.worktree.marks if agent.worktree else None,
        )

    async def supervise(self, session: AgentSession) -> SessionStatus:
        """Report whether the execution is running, finished, or overdue."""
        if session.pid is None:
            return SessionStatus.FINISHED

        process_alive = is_process_alive(session.pid)
        if not process_alive:
            return SessionStatus.FINISHED

        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)

        deadline = started_at + timedelta(seconds=self._timeout_seconds)
        current_time = datetime.now(UTC)
        if current_time > deadline:
            return SessionStatus.OVERDUE

        return SessionStatus.ALIVE

    async def stop(self, session: AgentSession) -> None:
        """Stop the execution and its child processes."""
        if session.pid is None:
            return

        try:
            os.killpg(session.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return

    def _get_resume_id(self, agent: NodeAgent) -> str:
        transcript_path = self._transcript_locator.get_transcript_path(agent)
        if transcript_path is None:
            raise WorktreeError("The Codex agent has no worktree.")

        try:
            thread_id = self._find_thread_id(transcript_path)
        except FileNotFoundError:
            if not agent.sessions and agent.resume_token:
                return agent.resume_token

            thread_id = None

        if thread_id is not None:
            return thread_id

        raise WorktreeError(
            "Codex did not record a thread ID; retry this node with --reset."
        )

    def _find_thread_id(self, transcript_path: Path) -> str | None:
        with transcript_path.open(encoding="utf-8", errors="replace") as transcript:
            for line in transcript:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                is_record = isinstance(record, dict)
                if not is_record:
                    continue

                record_type = record.get("type")
                thread_id = record.get("thread_id")
                valid_thread_id = isinstance(thread_id, str) and bool(thread_id)
                if record_type in ("thread.started", "dag.prompt") and valid_thread_id:
                    return str(thread_id)

        return None

    def _get_prompt_with_learnings(self, prompt: str) -> str:
        try:
            learnings = self._learnings_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return prompt
        except OSError as error:
            logger.warning("%s did not open: %s", self._learnings_path, error)

            return prompt

        if not learnings:
            return prompt

        learnings_section = format_label(
            LABELS["runLearnings"], {"learnings": learnings}
        )

        return prompt + learnings_section

    def _spawn(self, argv: list[str], agent: NodeAgent) -> int:
        transcript_path = self._transcript_locator.get_transcript_path(agent)
        if agent.worktree is None or transcript_path is None:
            raise WorktreeError("The Codex agent has no worktree.")

        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        exit_path = agent.worktree.get_exit_path()
        exit_path.unlink(missing_ok=True)
        wrapped_argv = [
            sys.executable,
            str(self._SESSION_RUNNER),
            str(exit_path),
            str(transcript_path),
            *argv,
        ]
        log_path = agent.worktree.get_log_path()
        with log_path.open("w") as log:
            process = subprocess.Popen(
                wrapped_argv,
                cwd=agent.worktree.absolute_path,
                env=dict(os.environ),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        return process.pid

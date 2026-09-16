"""The TranscriptLocator for the session files Claude Code writes."""

from __future__ import annotations

import re
from pathlib import Path

from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent

PROJECTS_HOME = Path.home() / ".claude" / "projects"
SESSION_FILE_SUFFIX = ".jsonl"
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^A-Za-z0-9]")
PROJECT_DIRECTORY_SEPARATOR = "-"


class ClaudeTranscriptLocator(TranscriptLocator):
    """Locates the session file Claude Code writes for an agent's worktree."""

    def get_transcript_path(self, agent: NodeAgent) -> Path | None:
        if not agent.resume_token or agent.worktree is None:
            return None

        project_directory = NON_ALPHANUMERIC_PATTERN.sub(
            PROJECT_DIRECTORY_SEPARATOR, agent.worktree.absolute_path
        )
        session_file = f"{agent.resume_token}{SESSION_FILE_SUFFIX}"

        return PROJECTS_HOME / project_directory / session_file

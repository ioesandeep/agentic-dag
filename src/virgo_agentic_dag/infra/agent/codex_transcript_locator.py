"""The TranscriptLocator for the transcript archive the session runner writes beside the worktree."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent

SESSION_FILE_SUFFIX = ".jsonl"
TRANSCRIPT_HOME_SUFFIX = ".sessions"


class CodexTranscriptLocator(TranscriptLocator):
    """Locates the transcript the session runner appends to across an agent's executions."""

    def get_transcript_path(self, agent: NodeAgent) -> Path | None:
        if not agent.resume_token or agent.worktree is None:
            return None

        token_bytes = agent.resume_token.encode("utf-8")
        token_hash = sha256(token_bytes).hexdigest()
        transcript_home = Path(agent.worktree.absolute_path).with_suffix(
            TRANSCRIPT_HOME_SUFFIX
        )

        return transcript_home / f"{token_hash}{SESSION_FILE_SUFFIX}"

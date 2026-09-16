"""Starts a learning agent session for the nodes due for learning extraction."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.learning.learning_prompt_composer import (
    LearningPromptComposer,
)
from virgo_agentic_dag.utils.create_session_token import create_session_token


class LearningDispatchService:
    """A service for starting a learning agent session with a batch of settled nodes."""

    def __init__(
        self,
        extraction_lock: ExtractionLock,
        prompt_composer: LearningPromptComposer,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        agent_launcher: AgentLauncher,
        executor_agent: ExecutorAgent,
        run_home: Path,
    ) -> None:
        self._extraction_lock = extraction_lock
        self._prompt_composer = prompt_composer
        self._node_repo = node_repo
        self._audit_entry_repo = audit_entry_repo
        self._agent_launcher = agent_launcher
        self._executor_agent = executor_agent
        self._learning_home = run_home / "learning"

    async def dispatch(self, current_time: datetime) -> TickResponse:
        """Start a learning session for the nodes due for extraction unless the lock is taken."""
        is_extraction_lock_free = self._extraction_lock.is_free()
        if not is_extraction_lock_free:
            return TickResponse()

        settled_nodes = await self._node_repo.get_nodes_due_for_learning_extraction()
        if not settled_nodes:
            return TickResponse()

        is_extraction_lock_acquired = self._extraction_lock.acquire()
        if not is_extraction_lock_acquired:
            return TickResponse()

        prompt = self._prompt_composer.compose_prompt(settled_nodes)
        agent_session = await self._launch(prompt, current_time)
        if agent_session.pid is not None:
            self._extraction_lock.record_session_pid(agent_session.pid)

        await self._node_repo.record_learnings_extracted(settled_nodes, current_time)
        audit_writes = [
            self._record_dispatch(node, current_time) for node in settled_nodes
        ]
        await asyncio.gather(*audit_writes)

        return TickResponse(sessions_started=1)

    async def _record_dispatch(self, node: Node, current_time: datetime) -> None:
        audit_entry = AuditEntry(
            node_id=node.id,
            state=node.state,
            note=LABELS["learningExtractionStarted"],
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)

    async def _launch(self, prompt: str, current_time: datetime) -> AgentSession:
        self._learning_home.mkdir(parents=True, exist_ok=True)

        session_token = create_session_token()
        learning_worktree = WorkTree(
            name="learning",
            absolute_path=str(self._learning_home),
            created_at=current_time,
        )
        learning_agent = NodeAgent(
            id="learning",
            name=self._executor_agent.value,
            resume_token=session_token,
            node_id="learning",
            worktree=learning_worktree,
        )
        graph_node = GraphNode(id="learning", executor_agent=self._executor_agent)

        return await self._agent_launcher.launch(graph_node, prompt, learning_agent)

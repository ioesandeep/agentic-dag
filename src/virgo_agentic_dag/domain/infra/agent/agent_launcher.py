"""The launcher interface for whichever agent product runs a node."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent


class AgentLauncher(ABC):
    """Starts, wakes, and supervises one agent's executions from persisted rows only."""

    @abstractmethod
    async def launch(
        self, graph_node: GraphNode, brief: str, agent: NodeAgent
    ) -> AgentSession:
        """Start a fresh execution for this agent in its worktree, resumable by its token."""

    @abstractmethod
    async def wake(
        self, graph_node: GraphNode, news: str, agent: NodeAgent
    ) -> AgentSession:
        """Resume this agent in its worktree with only the changes it has not seen."""

    @abstractmethod
    async def supervise(self, session: AgentSession) -> SessionStatus:
        """Report whether this execution is still working, finished, or past its deadline."""

    @abstractmethod
    async def stop(self, session: AgentSession) -> None:
        """End this execution and everything it started."""

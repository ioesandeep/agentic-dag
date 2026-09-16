"""Where each node's agent assignment lives, whatever database holds it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent


class NodeAgentRepo(ABC):
    """Reads and writes the agent assigned to a node."""

    @abstractmethod
    async def get_by_agent_id(self, agent_id: str) -> NodeAgent | None:
        """Return this agent, or None if no node was ever assigned one by this id."""

    @abstractmethod
    async def get_by_node_id(self, node_id: str) -> NodeAgent | None:
        """Return the agent working this node, or None before assignment."""

    @abstractmethod
    async def save(self, agent: NodeAgent) -> None:
        """Persist this agent as it now is."""

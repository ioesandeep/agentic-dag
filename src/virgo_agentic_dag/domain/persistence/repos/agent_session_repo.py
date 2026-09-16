"""The log of every execution an agent has run, whatever database holds it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession


class AgentSessionRepo(ABC):
    """Opens and closes execution rows, one explicit write each."""

    @abstractmethod
    async def add(self, session: AgentSession) -> None:
        """Record one execution as it starts, under the agent its row names."""

    @abstractmethod
    async def close(self, session: AgentSession) -> None:
        """Mark this session's row ended with its end state."""

    @abstractmethod
    async def get_open_sessions(self) -> list[AgentSession]:
        """Return every execution not yet ended, each carrying the agent that ran it."""

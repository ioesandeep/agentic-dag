"""The interface for terminating an agent session and recording its end."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession


class SessionKiller(ABC):
    """Terminates an agent session and closes the records that track it."""

    @abstractmethod
    async def kill(self, session: AgentSession, current_time: datetime) -> None:
        """Terminate this session and record its end state, idempotently."""

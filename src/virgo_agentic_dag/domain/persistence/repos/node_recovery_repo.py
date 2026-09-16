"""The record of every failure a node has had, whatever database stores it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery


class NodeRecoveryRepo(ABC):
    """Writes a row for each failure of a node and queries the rows written so far."""

    @abstractmethod
    async def add(self, node_recovery: NodeRecovery) -> None:
        """Record a single failure and the recovery decision for it."""

    @abstractmethod
    async def get_newest_recovery_by_node_id(self, node_id: str) -> NodeRecovery | None:
        """Return the last recorded failure of this node, or None before its first."""

    @abstractmethod
    async def get_due_recoveries(self, recover_at: datetime) -> list[NodeRecovery]:
        """Return the last recorded failure of each node when it is recoverable and eligible at or before the given recover_at."""

    @abstractmethod
    async def count_by_node_id(self, node_id: str) -> int:
        """Return the number of failures recorded for this node."""

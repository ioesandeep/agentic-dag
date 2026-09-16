"""One kind of change on a pull request that can wake its node, detected and described in one place."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.signals.signal_change import SignalChange


class PrSignal(ABC):
    """A single reason to wake a node, owning how it is detected, marked, and explained."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the key this signal's watermark is stored under."""

    @abstractmethod
    def detect(self, reading: PrDetails, mark: str) -> SignalChange | None:
        """Return what is new since the mark, or nothing when the node is already up to date."""

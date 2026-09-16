"""How far each signal has been acted on, keyed by signal, so adding a signal adds no column."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from virgo_agentic_dag.domain.signals.signal_change import SignalChange


@dataclass(frozen=True)
class SignalMarkIndex:
    """The per-signal watermark recording how far a node has been notified."""

    values: Mapping[str, str] = field(default_factory=dict)

    def read(self, signal: str) -> str:
        """Return how far this signal has been acted on, or empty when it never has."""
        return self.values.get(signal, "")

    def advanced(self, changes: Sequence[SignalChange]) -> SignalMarkIndex:
        """Return these marks advanced past every supplied change."""
        return SignalMarkIndex(
            dict(self.values) | {change.signal: change.mark for change in changes}
        )

    def without(self, signal: str) -> SignalMarkIndex:
        """Return these marks with one signal's watermark cleared."""
        return SignalMarkIndex(
            {name: mark for name, mark in self.values.items() if name != signal}
        )

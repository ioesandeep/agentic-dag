"""The identity of one continuous-integration failure, so a new failure earns a fresh budget."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from virgo_agentic_dag.domain.observation.check_failure import CheckFailure


@dataclass(frozen=True)
class CheckSignature:
    """Identifies a check failure by commit and check names, so repeat readings compare equal."""

    value: str = ""

    @classmethod
    def of(cls, head_sha: str, failures: Sequence[CheckFailure]) -> CheckSignature:
        """Build the signature a repair budget is spent against."""
        if not failures:
            return cls()

        names = sorted(failure.name for failure in failures)

        return cls("|".join((head_sha, *names)))

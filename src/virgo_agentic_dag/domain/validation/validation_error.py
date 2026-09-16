"""One finding a validation rule reported, with its blocking severity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    node_id: str | None = None
    is_fatal: bool = True

    def is_blocking(self) -> bool:
        """Report whether this finding blocks the run rather than only warning."""
        return self.is_fatal

"""The collected findings of every validation rule, and whether any blocks the run."""

from __future__ import annotations

from dataclasses import dataclass, field

from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


@dataclass(frozen=True)
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    def is_blocking(self) -> bool:
        """Report whether anything found here must stop the graph from running."""
        return any(error.is_blocking() for error in self.errors)

    def describe(self) -> str:
        """Return every finding as display lines, in the order they were reported."""
        return "".join(self._describe(error) for error in self.errors)

    def _describe(self, error: ValidationError) -> str:
        prefix = "" if error.is_blocking() else LABELS["findingWarningPrefix"]

        return format_label(
            LABELS["finding"],
            {"prefix": prefix, "code": error.code, "message": error.message},
        )

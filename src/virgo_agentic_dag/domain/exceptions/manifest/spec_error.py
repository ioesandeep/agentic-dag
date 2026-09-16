"""The error raised when a graph specification cannot be parsed into the model."""

from __future__ import annotations


class SpecError(ValueError):
    """Raised when a graph specification cannot be parsed into the domain model."""

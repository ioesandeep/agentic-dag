"""The error raised when a run asks for something this host cannot be set up to do."""

from __future__ import annotations


class ConfigError(ValueError):
    """Raised when a run's declared setup cannot be honoured on this host."""

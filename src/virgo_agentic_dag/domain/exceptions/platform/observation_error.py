"""The error raised when the controller cannot obtain a trustworthy external reading."""

from __future__ import annotations


class ObservationError(RuntimeError):
    """Raised when git or the hosting platform cannot be read well enough to decide anything."""

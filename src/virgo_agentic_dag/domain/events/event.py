"""The base type for anything that happens in a run and may be notified."""

from __future__ import annotations

from abc import ABC


class Event(ABC):
    """The abstract base every event extends, so a subscriber can bind to one subclass."""

"""A base event for a dag start or completion."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.events.event import Event


@dataclass(frozen=True)
class DagEvent(Event):
    dag_name: str

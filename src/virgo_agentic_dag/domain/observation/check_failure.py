"""One continuous-integration check that did not pass, and where its log lives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckFailure:
    name: str
    conclusion: str
    run_id: str = ""

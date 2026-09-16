"""Builds check failures from the platform's status rollup, keeping each one's run id."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from virgo_agentic_dag.domain.observation.check_failure import CheckFailure

FAILED_CONCLUSIONS = frozenset(
    {"FAILURE", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "STALE", "ACTION_REQUIRED"}
)

_RUN_ID = re.compile(r"/runs/(\d+)")


class CheckFailureMapper:
    """Keeps only the checks that did not pass, with the run whose log explains why."""

    def get_failures(
        self, checks: Sequence[dict[str, Any]]
    ) -> tuple[CheckFailure, ...]:
        return tuple(
            CheckFailure(
                name=str(check.get("name", "")),
                conclusion=str(check.get("conclusion", "")),
                run_id=self._get_run_id(str(check.get("detailsUrl", ""))),
            )
            for check in checks
            if check.get("conclusion") in FAILED_CONCLUSIONS
        )

    def get_settled(self, checks: Sequence[dict[str, Any]]) -> bool:
        """Report whether every check has finished, since one still running has no verdict yet."""
        return all(check.get("conclusion") for check in checks)

    def _get_run_id(self, details_url: str) -> str:
        found = _RUN_ID.search(details_url)

        return found.group(1) if found else ""

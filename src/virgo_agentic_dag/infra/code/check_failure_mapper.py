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
        """Identify checks that require a fix."""
        failures: list[CheckFailure] = []
        for check in checks:
            conclusion = check.get("conclusion", "")
            state = check.get("state", "")
            if conclusion not in FAILED_CONCLUSIONS and state not in {
                "FAILURE",
                "ERROR",
            }:
                continue

            name_value = check.get("name", "") or check.get("context", "")
            name = str(name_value)

            conclusion = conclusion or state
            conclusion = str(conclusion)

            url_value = check.get("detailsUrl", "") or check.get("targetUrl", "")
            details_url = str(url_value)
            run_id = self._get_run_id(details_url)

            failure = CheckFailure(name=name, conclusion=conclusion, run_id=run_id)
            failures.append(failure)

        return tuple(failures)

    def get_settled(self, checks: Sequence[dict[str, Any]]) -> bool:
        """Determine whether all checks have finished."""
        for check in checks:
            state = check.get("state")
            conclusion = check.get("conclusion")

            is_status_pending = state in {"PENDING", "EXPECTED"}
            is_check_pending = "state" not in check and not conclusion
            if is_status_pending or is_check_pending:
                return False

        return True

    def _get_run_id(self, details_url: str) -> str:
        found = _RUN_ID.search(details_url)

        return found.group(1) if found else ""

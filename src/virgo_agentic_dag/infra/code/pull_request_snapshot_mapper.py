"""Maps the hosting platform's pull-request JSON into a snapshot, flagging partial readings."""

from __future__ import annotations

from typing import Any

from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.infra.code.check_failure_mapper import CheckFailureMapper

REQUIRED_FIELDS: tuple[str, ...] = (
    "state",
    "headRefOid",
    "baseRefName",
    "mergeable",
    "reviewDecision",
    "statusCheckRollup",
)


class PullRequestSnapshotMapper:
    """Maps platform JSON to a PullRequestSnapshot, flagging incomplete readings."""

    def __init__(self, checks: CheckFailureMapper | None = None) -> None:
        self._checks = checks or CheckFailureMapper()

    def get_snapshot(self, payload: dict[str, Any]) -> PullRequestSnapshot:
        mergeable = payload.get("mergeable", "")
        state = self._get_state(payload)
        complete = all(field in payload for field in REQUIRED_FIELDS)
        still_computing = state is PullRequestState.OPEN and mergeable == "UNKNOWN"
        rollup = payload.get("statusCheckRollup") or []

        return PullRequestSnapshot(
            state=state,
            head_sha=str(payload.get("headRefOid", "")),
            base_branch=str(payload.get("baseRefName", "")),
            merge_commit_sha=self._get_merge_commit(payload),
            is_mergeable=mergeable != "CONFLICTING",
            has_changes_requested=payload.get("reviewDecision") == "CHANGES_REQUESTED",
            is_approved=payload.get("reviewDecision") == "APPROVED",
            title=str(payload.get("title") or ""),
            merged_by=self._get_merged_by(payload),
            failures=self._checks.get_failures(rollup),
            checks_settled=self._checks.get_settled(rollup),
            is_complete=complete and not still_computing,
        )

    def _get_state(self, payload: dict[str, Any]) -> PullRequestState:
        try:
            return PullRequestState(payload.get("state", ""))
        except ValueError:
            return PullRequestState.OPEN

    def _get_merged_by(self, payload: dict[str, Any]) -> str:
        merged_by = payload.get("mergedBy") or {}

        return str(merged_by.get("login", ""))

    def _get_merge_commit(self, payload: dict[str, Any]) -> str:
        merge_commit = payload.get("mergeCommit") or {}

        return str(merge_commit.get("oid", ""))

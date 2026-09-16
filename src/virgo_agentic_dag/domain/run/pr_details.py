"""The full platform reading of a node's pull request, refreshed every tick."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.observation.check_failure import CheckFailure
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact


@dataclass(frozen=True)
class PrDetails:
    """An uncached snapshot of a pull request as the platform reports it."""

    number: int
    head_sha: str
    base_branch: str = ""
    is_merged: bool = False
    is_open: bool = True
    is_conflicted: bool = False
    is_approved: bool = False
    title: str = ""
    merged_by: str = ""
    failures: tuple[CheckFailure, ...] = ()
    checks_settled: bool = True
    artifacts: tuple[ReviewArtifact, ...] = ()
    is_complete: bool = True

    def get_approver_name(self) -> str:
        """Return the login that approved this pull request, or empty when none has."""
        for artifact in reversed(self.artifacts):
            if artifact.is_approval:
                return artifact.author

        return ""

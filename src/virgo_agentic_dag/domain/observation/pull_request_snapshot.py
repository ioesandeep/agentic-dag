"""One raw reading of a pull request from the remote platform, before local verification."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.observation.check_failure import CheckFailure
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.run.pr_details import PrDetails


@dataclass(frozen=True)
class PullRequestSnapshot:
    state: PullRequestState
    head_sha: str
    base_branch: str
    merge_commit_sha: str = ""
    is_mergeable: bool = True
    has_changes_requested: bool = False
    is_approved: bool = False
    merged_by: str = ""
    title: str = ""
    url: str = ""
    failures: tuple[CheckFailure, ...] = ()
    checks_settled: bool = True
    is_complete: bool = True

    def to_pr_details(self, number: int) -> PrDetails:
        """Convert a pull request snapshot to details with the specified number."""
        return PrDetails(
            number=number,
            head_sha=self.head_sha,
            base_branch=self.base_branch,
            is_merged=self.state is PullRequestState.MERGED,
            is_open=self.state is PullRequestState.OPEN,
            is_conflicted=not self.is_mergeable,
            is_approved=self.is_approved,
            title=self.title,
            url=self.url,
            merged_by=self.merged_by,
            failures=self.failures,
            checks_settled=self.checks_settled,
            is_complete=self.is_complete,
        )

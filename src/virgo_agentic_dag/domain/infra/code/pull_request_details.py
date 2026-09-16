"""What adoption needs to know about a pull request, read once from the platform."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PullRequestDetails:
    number: int
    # owner/name of the repository the pull request lives in
    repository: str
    url: str
    head_branch: str
    # the pull request's own title, which names the work a node adopting it takes on
    title: str = ""

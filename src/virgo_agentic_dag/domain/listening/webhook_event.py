"""The GitHub webhook deliveries the framework reacts to."""

from __future__ import annotations

from enum import Enum


class WebhookEvent(Enum):
    """A delivery kind that can change what the next reconcile tick would observe."""

    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    ISSUE_COMMENT = "issue_comment"
    CHECK_SUITE = "check_suite"
    CHECK_RUN = "check_run"
    PUSH = "push"

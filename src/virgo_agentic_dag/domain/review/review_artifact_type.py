"""The kinds of review artifact a human can leave, each with its own id space."""

from __future__ import annotations

from enum import Enum


class ReviewArtifactType(Enum):
    ISSUE_COMMENT = "issue_comment"
    REVIEW_COMMENT = "review_comment"
    REVIEW = "review"

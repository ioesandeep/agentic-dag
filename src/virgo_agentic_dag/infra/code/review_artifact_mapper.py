"""Maps the platform's comment and review JSON into review artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType

_BLOCKING_REVIEW = "CHANGES_REQUESTED"
_APPROVING_REVIEW = "APPROVED"


class ReviewArtifactMapper:
    """Builds artifacts from platform JSON, dropping reviews that carry no feedback at all."""

    def get_all(
        self, kind: ReviewArtifactType, entries: Sequence[dict[str, Any]]
    ) -> tuple[ReviewArtifact, ...]:
        built = (self._get_one(kind, entry) for entry in entries)

        return tuple(artifact for artifact in built if artifact is not None)

    def _get_one(
        self, kind: ReviewArtifactType, entry: dict[str, Any]
    ) -> ReviewArtifact | None:
        body = str(entry.get("body") or "").strip()
        state = str(entry.get("state") or "")
        if kind is ReviewArtifactType.REVIEW and not body and state != _BLOCKING_REVIEW:
            return None

        if kind is not ReviewArtifactType.REVIEW and not body:
            return None

        author = entry.get("user") or {}

        return ReviewArtifact(
            kind=kind,
            artifact_id=int(entry.get("id", 0)),
            author=str(author.get("login", "")),
            body=body,
            created_at=str(entry.get("submitted_at") or entry.get("created_at") or ""),
            path=str(entry.get("path") or ""),
            updated_at=str(entry.get("updated_at") or ""),
            is_approval=kind is ReviewArtifactType.REVIEW
            and state == _APPROVING_REVIEW,
        )

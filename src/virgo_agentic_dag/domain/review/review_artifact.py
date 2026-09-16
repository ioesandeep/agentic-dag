"""One comment or review on a pull request that a node may still have to answer."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType


@dataclass(frozen=True)
class ReviewArtifact:
    kind: ReviewArtifactType
    artifact_id: int
    author: str
    body: str
    created_at: str
    path: str = ""
    updated_at: str = ""
    is_approval: bool = False

    def get_key(self) -> tuple[str, int]:
        """Return the kind and id that uniquely identify this artifact."""
        return self.kind.value, self.artifact_id

    def get_timestamp(self) -> str:
        """Return this artifact's last-modified timestamp, so an edit registers as new."""
        return max(self.updated_at, self.created_at)

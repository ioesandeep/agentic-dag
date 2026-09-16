"""Wakes a node when a human has written on its pull request since it last worked."""

from __future__ import annotations

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.signals.signal_change import SignalChange
from virgo_agentic_dag.services.signals.pr_signal import PrSignal

SIGNAL_NAME = "comments"


class CommentSignal(PrSignal):
    """Reports comments newer than the node's watermark, from anyone but the node itself."""

    def __init__(self, agent_account: str) -> None:
        self._agent_account = agent_account

    @property
    def name(self) -> str:
        return SIGNAL_NAME

    def detect(self, reading: PrDetails, mark: str) -> SignalChange | None:
        fresh = tuple(
            artifact
            for artifact in reading.artifacts
            if artifact.author != self._agent_account
            and not artifact.is_approval
            and artifact.get_timestamp() > mark
        )
        if not fresh:
            return None

        return SignalChange(
            signal=self.name,
            mark=max(artifact.get_timestamp() for artifact in fresh),
            heading=f"New review comments ({len(fresh)})",
            notification=NotificationType.FEEDBACK_RECEIVED,
            count=len(fresh),
            body="\n\n".join(self._render_one(artifact) for artifact in fresh),
        )

    def _render_one(self, artifact: ReviewArtifact) -> str:
        where = f" on `{artifact.path}`" if artifact.path else ""

        return f"**{artifact.author}**{where} (id {artifact.artifact_id}):\n{artifact.body}"

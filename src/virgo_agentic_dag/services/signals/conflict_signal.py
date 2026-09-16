"""Wakes a node when its pull request conflicts with the base branch at a commit it has not tried."""

from __future__ import annotations

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.signals.signal_change import SignalChange
from virgo_agentic_dag.services.signals.pr_signal import PrSignal

SIGNAL_NAME = "conflict"


class ConflictSignal(PrSignal):
    """Reports a conflict once per commit, so a failed resolution escalates instead of repeating."""

    @property
    def name(self) -> str:
        return SIGNAL_NAME

    def detect(self, reading: PrDetails, mark: str) -> SignalChange | None:
        if not reading.is_conflicted or reading.head_sha == mark:
            return None

        return SignalChange(
            signal=self.name,
            mark=reading.head_sha,
            heading="Conflicts with the base branch",
            notification=NotificationType.CONFLICTS_FOUND,
            body=self._render_instructions(reading.base_branch),
        )

    def _render_instructions(self, base_branch: str) -> str:
        base = base_branch or "the base branch"

        return (
            "This pull request no longer merges cleanly. Merge the base branch into "
            "yours, resolve the conflicts, and push the result:\n\n"
            f"    git fetch origin {base}\n"
            f"    git merge origin/{base}\n\n"
            "Merge rather than rebase: your commits are already pushed, so rewriting "
            "them would need the force-push you must never do. A merge commit pushes "
            "cleanly."
        )

"""Reports that a reviewer approved a pull request, which is news for a human and not work."""

from __future__ import annotations

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.signals.signal_change import SignalChange
from virgo_agentic_dag.services.signals.pr_signal import PrSignal

SIGNAL_NAME = "approval"


class ApprovalSignal(PrSignal):
    """Reports an approval once per head commit without waking the node."""

    @property
    def name(self) -> str:
        return SIGNAL_NAME

    def detect(self, reading: PrDetails, mark: str) -> SignalChange | None:
        if not reading.is_approved or reading.head_sha == mark:
            return None

        return SignalChange(
            signal=self.name,
            mark=reading.head_sha,
            heading="Approved",
            body="a reviewer approved this pull request",
            wakes_node=False,
            notification=NotificationType.APPROVED,
        )

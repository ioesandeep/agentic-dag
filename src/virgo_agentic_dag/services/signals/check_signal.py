"""Wakes a node when its pull request is failing checks it has not already tried to fix."""

from __future__ import annotations

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.observation.check_signature import CheckSignature
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.signals.signal_change import SignalChange
from virgo_agentic_dag.services.signals.pr_signal import PrSignal

SIGNAL_NAME = "checks"


class CheckSignal(PrSignal):
    """Reports failing checks whose commit-and-check identity the node has not seen before."""

    @property
    def name(self) -> str:
        return SIGNAL_NAME

    def detect(self, reading: PrDetails, mark: str) -> SignalChange | None:
        signature = CheckSignature.of(reading.head_sha, reading.failures)
        if not signature.value or signature.value == mark:
            return None

        return SignalChange(
            signal=self.name,
            mark=signature.value,
            heading="Failing checks",
            notification=NotificationType.CI_FAILED,
            body="\n".join(
                f"- `{failure.name}` ({failure.conclusion})"
                for failure in reading.failures
            ),
        )

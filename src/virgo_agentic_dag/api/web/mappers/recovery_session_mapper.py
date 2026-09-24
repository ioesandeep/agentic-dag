"""Converts recovery sessions to API responses."""

from __future__ import annotations

from datetime import UTC

from virgo_agentic_dag.api.web.api_responses.recovery_session_response import (
    RecoverySessionResponse,
)
from virgo_agentic_dag.api.web.utils.to_utc import to_utc
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)


def to_recovery_session_list_response(
    recovery_sessions: list[RecoverySession],
) -> list[RecoverySessionResponse]:
    """Convert every recovery session to its API response."""
    return [
        _to_recovery_session_response(recovery_session)
        for recovery_session in recovery_sessions
    ]


def _to_recovery_session_response(
    recovery_session: RecoverySession,
) -> RecoverySessionResponse:
    """Convert a single recovery session to its API response."""
    return RecoverySessionResponse(
        id=recovery_session.id,
        started_at=recovery_session.started_at.replace(tzinfo=UTC),
        ended_at=to_utc(recovery_session.ended_at),
        node_ids=recovery_session.get_node_ids(),
        is_process_alive=recovery_session.is_process_alive(),
    )

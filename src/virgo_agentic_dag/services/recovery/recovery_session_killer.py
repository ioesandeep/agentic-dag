from datetime import datetime

from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller
from virgo_agentic_dag.domain.persistence.entities.recovery_session import (
    RecoverySession,
)
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)


class RecoverySessionKiller:
    """Prevents a recovery agent from continuing after its session ends."""

    def __init__(
        self, recovery_session_repo: RecoverySessionRepo, process_killer: ProcessKiller
    ) -> None:
        self._recovery_session_repo = recovery_session_repo
        self._process_killer = process_killer

    async def kill(
        self, recovery_session: RecoverySession, current_time: datetime
    ) -> None:
        """End the recovery agent's execution."""
        is_recovery_process_alive = recovery_session.is_process_alive()
        if is_recovery_process_alive and recovery_session.pid is not None:
            self._process_killer.kill(recovery_session.pid)

        closed_recovery_session = RecoverySession(
            id=recovery_session.id,
            session_token=recovery_session.session_token,
            pid=recovery_session.pid,
            started_at=recovery_session.started_at,
            ended_at=current_time,
            node_ids=recovery_session.node_ids,
        )
        await self._recovery_session_repo.close(closed_recovery_session)

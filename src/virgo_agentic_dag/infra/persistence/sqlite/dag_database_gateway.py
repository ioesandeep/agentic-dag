"""The gateway to one dag's database."""

from __future__ import annotations

from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_scheduled_job_repo import (
    SqliteScheduledJobRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_slack_notification_repo import (
    SqliteSlackNotificationRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_watcher_repo import (
    SqliteWatcherRepo,
)


class DagDatabaseGateway:
    """One dag's database and the repositories that read it."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database
        self.node_repo: NodeRepo = SqliteNodeRepo(database)
        self.node_recovery_repo: NodeRecoveryRepo = SqliteNodeRecoveryRepo(database)
        self.audit_entry_repo: AuditEntryRepo = SqliteAuditEntryRepo(database)
        self.scheduled_job_repo: ScheduledJobRepo = SqliteScheduledJobRepo(database)
        self.slack_notification_repo: SlackNotificationRepo = (
            SqliteSlackNotificationRepo(database)
        )
        self.watcher_repo: WatcherRepo = SqliteWatcherRepo(database)

    async def dispose(self) -> None:
        """Close this dag's database."""
        await self._database.dispose()

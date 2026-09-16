"""Runs the `status` command, printing what the run's database records."""

from __future__ import annotations

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.status_command import StatusCommand
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.infra.streaming.stream_health_check import (
    StreamHealthCheck,
)
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


class StatusCommandHandler(CommandHandler[StatusCommand]):
    """Reports a run's nodes, open sessions, watcher, schedule, and sse bridge health."""

    def __init__(
        self,
        node_repo: NodeRepo,
        agent_session_repo: AgentSessionRepo,
        watcher_repo: WatcherRepo,
        scheduled_job_repo: ScheduledJobRepo,
        dag_loader: DagLoader,
        stream_health_check: StreamHealthCheck,
    ) -> None:
        self._node_repo = node_repo
        self._agent_session_repo = agent_session_repo
        self._watcher_repo = watcher_repo
        self._scheduled_job_repo = scheduled_job_repo
        self._dag_loader = dag_loader
        self._stream_health_check = stream_health_check

    async def handle(self, command: StatusCommand) -> ExitCode:
        nodes = await self._node_repo.get_all()
        sessions = await self._agent_session_repo.get_open_sessions()
        watcher = await self._watcher_repo.get_by_dag_name(command.dag_name)
        job = await self._scheduled_job_repo.get_by_dag_name(command.dag_name)

        if not nodes and not sessions and watcher is None and job is None:
            emit(format_label(LABELS["statusEmpty"], {"dag": command.dag_name}))

            return ExitCode.SUCCESS

        self._report_nodes(nodes)
        self._report_sessions(sessions)
        self._report_watcher(watcher)
        self._report_job(job)
        await self._report_sse_health(job)

        return ExitCode.SUCCESS

    def _report_nodes(self, nodes: list[Node]) -> None:
        for node in nodes:
            args = {"node_id": node.id, "state": node.state}
            emit(format_label(LABELS["statusNode"], args))

    def _report_sessions(self, sessions: list[AgentSession]) -> None:
        for session in sessions:
            args = {
                "agent_id": session.agent_id,
                "pid": session.pid,
                "trigger": session.triggered_by,
            }
            emit(format_label(LABELS["statusSession"], args))

    def _report_watcher(self, watcher: Watcher | None) -> None:
        if watcher is None:
            return

        emit(format_label(LABELS["statusWatcher"], {"pid": watcher.pid}))

    def _report_job(self, job: ScheduledJob | None) -> None:
        if job is None:
            return

        args = {"job": job.label, "seconds": job.interval_seconds}
        emit(format_label(LABELS["statusJob"], args))

    async def _report_sse_health(self, job: ScheduledJob | None) -> None:
        sse_url = self._get_sse_url(job)
        if sse_url is None:
            return

        health = await self._stream_health_check.check(sse_url)
        label = "statusBridgeAlive" if health.is_alive else "statusBridgeUnreachable"

        emit(format_label(LABELS[label], {"url": health.url}))

    def _get_sse_url(self, job: ScheduledJob | None) -> str | None:
        if job is None:
            return None

        dag_path = job.get_dag_path()
        if dag_path is None:
            return None

        return self._dag_loader.load(dag_path).sse_url or None

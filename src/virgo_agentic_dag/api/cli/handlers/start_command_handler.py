"""Runs one pass, then registers the host job that re-runs it until the run completes."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.start_command import StartCommand
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.events.dag_completed_event import DagCompletedEvent
from virgo_agentic_dag.domain.events.dag_started_event import DagStartedEvent
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)
from virgo_agentic_dag.services.watching.watcher_service import WatcherService
from virgo_agentic_dag.utils.format_label import format_label


class StartCommandHandler(CommandHandler[StartCommand]):
    """Advances a run one pass, then reconciles the host's schedule against what it found."""

    def __init__(
        self,
        tick_command_handler: CommandHandler[TickCommand],
        scheduler_factory: SchedulerFactory,
        scheduled_job_repo: ScheduledJobRepo,
        node_repo: NodeRepo,
        scheduled_job_builder: ScheduledJobBuilder,
        watcher_service: WatcherService,
        dag_spec: DagSpec,
        notification_publisher: NotificationPublisher,
    ) -> None:
        self._tick_command_handler = tick_command_handler
        self._scheduler_factory = scheduler_factory
        self._scheduled_job_repo = scheduled_job_repo
        self._node_repo = node_repo
        self._scheduled_job_builder = scheduled_job_builder
        self._watcher_service = watcher_service
        self._dag_spec = dag_spec
        self._notification_publisher = notification_publisher

    async def handle(self, command: StartCommand) -> ExitCode:
        exit_code = await self._tick_command_handler.handle(command)
        # TODO: count consecutive failures and retire the job past a threshold
        if exit_code is ExitCode.FAILURE:
            return exit_code

        dag_name = self._scheduled_job_builder.get_dag_name()
        if exit_code is ExitCode.RUN_COMPLETE:
            await self._conclude(dag_name)

            return exit_code

        scheduled_job = await self._register(command)
        if scheduled_job is not None:
            await self._publish_dag_started(dag_name)

        if self._dag_spec.sse_url:
            await self._watcher_service.watch(dag_name)

        return exit_code

    async def _conclude(self, dag_name: str) -> None:
        """Complete every durable shutdown step before any kill that could target this process."""
        await self._publish_dag_completed(dag_name)
        await self._notification_publisher.drain()

        watcher = await self._watcher_service.forget(dag_name)
        await self._retire()

        if watcher is not None:
            self._watcher_service.kill(watcher)

    async def _register(self, command: StartCommand) -> ScheduledJob | None:
        """Register the host job that wakes this run, or return None when the host already wakes it."""
        job = self._scheduled_job_builder.build(command, datetime.now(UTC))
        scheduler = self._scheduler_factory.get_scheduler()
        if await scheduler.is_registered(job):
            return None

        await scheduler.register(job)
        await self._scheduled_job_repo.save(job)
        emit(format_label(LABELS["runScheduled"], {"job": job.label}) + "\n")

        return job

    async def _publish_dag_started(self, dag_name: str) -> None:
        nodes = await self._node_repo.get_all()
        in_progress_nodes = [
            node for node in nodes if node.state == NodeState.IN_PROGRESS.value
        ]

        dag_started_event = DagStartedEvent(
            dag_name=dag_name,
            node_count=len(nodes),
            in_progress_node_count=len(in_progress_nodes),
        )
        self._notification_publisher.publish(dag_started_event)

    async def _publish_dag_completed(self, dag_name: str) -> None:
        nodes = await self._node_repo.get_all()
        current_time = datetime.now(UTC)
        created_times = [node.created_at.replace(tzinfo=UTC) for node in nodes]
        elapsed_time = current_time - min(created_times, default=current_time)

        node_counts_by_state = Counter(NodeState(node.state) for node in nodes)
        dag_completed_event = DagCompletedEvent(
            dag_name=dag_name,
            node_counts_by_state=node_counts_by_state,
            elapsed_time=elapsed_time,
        )
        self._notification_publisher.publish(dag_completed_event)

    async def _retire(self) -> None:
        dag_name = self._scheduled_job_builder.get_dag_name()
        job = await self._scheduled_job_repo.get_by_dag_name(dag_name)
        if job is None:
            return

        await self._scheduled_job_repo.delete(job)
        emit(format_label(LABELS["runUnscheduled"], {"job": job.label}) + "\n")

        scheduler = self._scheduler_factory.get_scheduler()
        await scheduler.retire(job)

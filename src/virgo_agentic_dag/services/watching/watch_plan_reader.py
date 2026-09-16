"""Builds a watcher's plan and topics from the run's database and dag file."""

from __future__ import annotations

from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.services.watching.watch_plan import WatchPlan


class WatchPlanReader:
    """Builds a watcher's plan from the scheduled job, and its topics from the worktrees."""

    def __init__(
        self,
        scheduled_job_repo: ScheduledJobRepo,
        work_tree_repo: WorkTreeRepo,
        code_repo: CodeRepo,
        dag_loader: DagLoader,
    ) -> None:
        self._scheduled_job_repo = scheduled_job_repo
        self._work_tree_repo = work_tree_repo
        self._code_repo = code_repo
        self._dag_loader = dag_loader

    async def get_plan(self, command: WatchCommand) -> WatchPlan:
        """Return the watcher's fixed plan, read from the run's own records."""
        job = await self._get_job(command)
        dag_path = job.get_dag_path()
        if dag_path is None:
            raise ConfigError(f"the job for {command.dag_name} names no dag file")

        spec = self._dag_loader.load(dag_path)
        sse_url = command.sse_url or spec.sse_url
        if not sse_url:
            raise ConfigError(
                f"{command.dag_name} has no event stream; pass --sse or set sse_url"
            )

        project_root = spec.project_root or job.get_working_directory()
        repo_slug = await self._code_repo.get_repo_slug(project_root)

        return WatchPlan(
            sse_url=sse_url,
            argv=tuple(job.get_argv()),
            working_directory=job.get_working_directory(),
            repo_slug=repo_slug,
            refresh_seconds=spec.tick_interval_seconds,
        )

    async def get_topics(self, plan: WatchPlan) -> list[str]:
        """Return the topics the watcher should subscribe to right now."""
        worktrees = await self._work_tree_repo.get_published()
        topics = {f"{plan.repo_slug}#{worktree.pr_number}" for worktree in worktrees}

        return sorted(topics)

    async def is_scheduled(self, dag_name: str) -> bool:
        """Report whether this run still has a job on the host."""
        job = await self._scheduled_job_repo.get_by_dag_name(dag_name)

        return job is not None

    async def _get_job(self, command: WatchCommand) -> ScheduledJob:
        job = await self._scheduled_job_repo.get_by_dag_name(command.dag_name)
        if job is None:
            raise ConfigError(
                f"{command.dag_name} is not scheduled; start the run before watching it"
            )

        return job

"""The long-running watch loop that debounces pull request events into passes."""

from __future__ import annotations

import asyncio
import time

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.host.sleeper import Sleeper
from virgo_agentic_dag.domain.listening.webhook_event import WebhookEvent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.watching.event_reader import EventReader
from virgo_agentic_dag.services.watching.subscription_factory import SubscriptionFactory
from virgo_agentic_dag.services.watching.watch_plan import WatchPlan
from virgo_agentic_dag.services.watching.watch_plan_reader import WatchPlanReader
from virgo_agentic_dag.utils.format_label import format_label

DEBOUNCE_SECONDS = 60.0

NO_TOPICS_SECONDS = 60.0


class RunWatcher:
    """Turns a run's pull request events into debounced passes."""

    def __init__(
        self,
        plan_reader: WatchPlanReader,
        subscription_factory: SubscriptionFactory,
        command_runner: CommandRunner,
        sleeper: Sleeper,
        debounce_seconds: float = DEBOUNCE_SECONDS,
        no_topics_seconds: float = NO_TOPICS_SECONDS,
    ) -> None:
        self._plan_reader = plan_reader
        self._subscription_factory = subscription_factory
        self._command_runner = command_runner
        self._sleeper = sleeper
        self._debounce_seconds = debounce_seconds
        self._no_topics_seconds = no_topics_seconds

    async def watch(self, command: WatchCommand) -> ExitCode:
        """Watch the run's pull requests until the run completes."""
        plan = await self._plan_reader.get_plan(command)

        while True:
            topics = await self._plan_reader.get_topics(plan)
            if not topics:
                if not await self._plan_reader.is_scheduled(command.dag_name):
                    emit(format_label(LABELS["watchEnded"]) + "\n")

                    return ExitCode.RUN_COMPLETE

                await asyncio.to_thread(self._sleeper.sleep, self._no_topics_seconds)
                continue

            exit_code = await self._watch_subscription(plan, topics)
            if exit_code is ExitCode.RUN_COMPLETE:
                emit(format_label(LABELS["watchEnded"]) + "\n")

                return exit_code

    async def _watch_subscription(self, plan: WatchPlan, topics: list[str]) -> ExitCode:
        reader = self._subscription_factory.build(plan.sse_url, topics)
        reader.start()

        try:
            return await self._consume(plan, reader)
        finally:
            reader.stop()

    async def _consume(self, plan: WatchPlan, reader: EventReader) -> ExitCode:
        deadline: float | None = None
        while True:
            timeout = self._get_timeout(plan, deadline)
            payload = await asyncio.to_thread(reader.get_event, timeout)
            if payload is None and deadline is None:
                return ExitCode.SUCCESS

            if payload is None:
                return await self._fire(plan)

            if WebhookEvent._value2member_map_.get(payload) is None:
                continue

            deadline = time.monotonic() + self._debounce_seconds

    def _get_timeout(self, plan: WatchPlan, deadline: float | None) -> float:
        if deadline is None:
            return float(plan.refresh_seconds)

        return max(0.0, deadline - time.monotonic())

    async def _fire(self, plan: WatchPlan) -> ExitCode:
        result = await asyncio.to_thread(
            self._command_runner.run, plan.argv, plan.working_directory
        )
        emit(format_label(LABELS["watchFired"], {"code": result.returncode}) + "\n")

        if result.returncode == int(ExitCode.RUN_COMPLETE):
            return ExitCode.RUN_COMPLETE

        return ExitCode.SUCCESS

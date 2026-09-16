"""Reaching Slack as the run's own bot, keeping each node's story in one thread."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.checks_completed_event import ChecksCompletedEvent
from virgo_agentic_dag.domain.events.comments_added_event import CommentsAddedEvent
from virgo_agentic_dag.domain.events.comments_addressed_event import (
    CommentsAddressedEvent,
)
from virgo_agentic_dag.domain.events.commit_pushed_event import CommitPushedEvent
from virgo_agentic_dag.domain.events.dag_completed_event import DagCompletedEvent
from virgo_agentic_dag.domain.events.dag_event import DagEvent
from virgo_agentic_dag.domain.events.dag_started_event import DagStartedEvent
from virgo_agentic_dag.domain.events.event import Event
from virgo_agentic_dag.domain.events.mergeability_changed_event import (
    MergeabilityChangedEvent,
)
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.node_retried_event import NodeRetriedEvent
from virgo_agentic_dag.domain.events.node_skipped_event import NodeSkippedEvent
from virgo_agentic_dag.domain.events.pull_request_adopted_event import (
    PullRequestAdoptedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_approved_event import (
    PullRequestApprovedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_merged_event import (
    PullRequestMergedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_opened_event import (
    PullRequestOpenedEvent,
)
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster
from virgo_agentic_dag.domain.infra.messaging.notification_dispatcher import (
    NotificationDispatcher,
)
from virgo_agentic_dag.domain.notifications.notification_composer import (
    NotificationComposer,
)
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)

logger = logging.getLogger(__name__)

_POST_MESSAGE = "https://slack.com/api/chat.postMessage"
_UPDATE_MESSAGE = "https://slack.com/api/chat.update"
_ADD_REACTION = "https://slack.com/api/reactions.add"

_ALREADY_THERE = "already_reacted"

_REACTIONS: dict[NotificationType, tuple[str, ...]] = {
    NotificationType.APPROVED: ("white_check_mark",),
    NotificationType.MERGED: ("tada",),
    NotificationType.APPROVED_AND_MERGED: ("white_check_mark", "tada"),
    NotificationType.CLOSED: ("x",),
    NotificationType.CANCELLED: ("x",),
    NotificationType.SUPERSEDED: ("white_check_mark",),
    NotificationType.NEEDS_HUMAN: ("warning",),
}

_BROADCAST_TYPES = frozenset(
    {NotificationType.NEEDS_HUMAN, NotificationType.AGENT_FAILED}
)


class BotNotificationDispatcher(NotificationDispatcher):
    """Speaks as the run's own bot, opening a thread per node and replying in it after."""

    def __init__(
        self,
        poster: JsonPoster,
        slack_notification_repo: SlackNotificationRepo,
        channel: str,
        composer: NotificationComposer,
        dag_name: str,
    ) -> None:
        self._poster = poster
        self._slack_notification_repo = slack_notification_repo
        self._channel = channel
        self._token = os.getenv("SLACK_BOT_TOKEN", "")
        self._composer = composer
        self._dag_name = dag_name

    async def dispatch(self, event: Event) -> None:
        if not self._token:
            logger.debug("no slack bot token, %s stays unsent", type(event).__name__)

            return

        match event:
            case NodeEvent():
                await self._dispatch_node_event(event)
            case DagEvent():
                await self._dispatch_dag_event(event)

    async def _dispatch_node_event(self, event: NodeEvent) -> None:
        opened = await self._slack_notification_repo.get_by_node_id(event.node_id)
        thread_id = opened.thread_id if opened is not None else ""

        if thread_id:
            await self._react(thread_id, event.type)

        message = self._compose(event)
        if not message:
            logger.debug("no %s message for %s", event.type.value, event.node_id)

            return

        is_pull_request_opened = isinstance(event, PullRequestOpenedEvent)
        if is_pull_request_opened and thread_id:
            await self._update_thread_message(event, message, thread_id)

            return

        payload = self._get_node_payload(event, message, thread_id)
        posted_id = await self._post(_POST_MESSAGE, payload, event.node_id)
        if not posted_id or thread_id:
            return

        slack_notification = SlackNotification(
            node_id=event.node_id,
            channel=self._channel,
            thread_id=posted_id,
            created_at=event.created_at,
        )
        await self._slack_notification_repo.save(slack_notification)

    async def _dispatch_dag_event(self, event: DagEvent) -> None:
        message = self._compose(event)
        if not message:
            logger.debug("no message for dag %s", event.dag_name)

            return

        payload: dict[str, Any] = {
            "channel": self._channel,
            "text": message,
            "blocks": [self._get_section_block(message)],
        }
        await self._post(_POST_MESSAGE, payload, event.dag_name)

    def _compose(self, event: Event) -> str:
        match event:
            case WorkStartedEvent():
                return self._composer.work_started(event)
            case PullRequestAdoptedEvent():
                return self._composer.pull_request_adopted(event)
            case PullRequestOpenedEvent():
                return self._composer.pull_request_opened(event)
            case CommitPushedEvent():
                return self._composer.commit_pushed(event)
            case CommentsAddedEvent():
                return self._composer.comments_added(event)
            case CommentsAddressedEvent():
                return self._composer.comments_addressed(event)
            case ChecksCompletedEvent():
                return self._composer.checks_completed(event)
            case MergeabilityChangedEvent():
                return self._composer.mergeability_changed(event)
            case PullRequestApprovedEvent():
                return self._composer.pull_request_approved(event)
            case PullRequestMergedEvent():
                return self._composer.pull_request_merged(event)
            case AgentStoppedEvent():
                return self._composer.agent_stopped(event)
            case NodeRetriedEvent():
                return self._composer.node_retried(event)
            case NodeSkippedEvent():
                return self._composer.node_skipped(event)
            case DagStartedEvent():
                return self._composer.dag_started(event)
            case DagCompletedEvent():
                return self._composer.dag_completed(event)
            case _:
                return ""

    async def _update_thread_message(
        self, event: NodeEvent, message: str, thread_id: str
    ) -> None:
        payload: dict[str, Any] = {
            "channel": self._channel,
            "ts": thread_id,
            "text": message,
            "blocks": self._get_blocks(event, message),
        }
        await self._post(_UPDATE_MESSAGE, payload, event.node_id)

    async def _post(self, url: str, payload: dict[str, Any], subject: str) -> str:
        reply = await asyncio.to_thread(self._poster.post, url, payload, self._token)
        if reply.get("ok"):
            return str(reply.get("ts", ""))

        logger.warning(
            "slack refused the notification for %s: %s",
            subject,
            reply.get("error") or "no response",
        )

        return ""

    def _get_node_payload(
        self, event: NodeEvent, message: str, thread_id: str
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "channel": self._channel,
            "text": message,
            "blocks": self._get_blocks(event, message),
        }
        if thread_id:
            payload["thread_ts"] = thread_id

        if event.type in _BROADCAST_TYPES:
            payload["reply_broadcast"] = True

        return payload

    def _get_blocks(self, event: NodeEvent, message: str) -> list[dict[str, Any]]:
        context_line = f"{self._dag_name} · {event.node_id} · {event.type.value}"

        return [
            self._get_section_block(message),
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": context_line}],
            },
        ]

    def _get_section_block(self, message: str) -> dict[str, Any]:
        return {"type": "section", "text": {"type": "mrkdwn", "text": message}}

    async def _react(self, thread_id: str, notification_type: NotificationType) -> None:
        for reaction in _REACTIONS.get(notification_type, ()):
            payload = {
                "channel": self._channel,
                "timestamp": thread_id,
                "name": reaction,
            }

            reply = await asyncio.to_thread(
                self._poster.post, _ADD_REACTION, payload, self._token
            )
            if reply.get("ok") or reply.get("error") == _ALREADY_THERE:
                continue

            logger.warning(
                "slack refused the %s reaction: %s",
                reaction,
                reply.get("error") or "no response",
            )

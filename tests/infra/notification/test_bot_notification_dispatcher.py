from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.checks_completed_event import ChecksCompletedEvent
from virgo_agentic_dag.domain.events.comments_added_event import CommentsAddedEvent
from virgo_agentic_dag.domain.events.comments_addressed_event import (
    CommentsAddressedEvent,
)
from virgo_agentic_dag.domain.events.mergeability_changed_event import (
    MergeabilityChangedEvent,
)
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.node_event_fields import NodeEventFields
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
from virgo_agentic_dag.domain.events.work_resumed_event import WorkResumedEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster
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
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.infra.notification.bot_notification_dispatcher import (
    BotNotificationDispatcher,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 7, 31, tzinfo=UTC)
READING = PrDetails(number=42, head_sha="8bddf07abcdef", title="Add a digest helper")


def build_fields(notification_type: NotificationType) -> NodeEventFields:
    return NodeEventFields(
        node_id="A",
        type=notification_type,
        created_at=NOW,
        updated_at=NOW,
        title="Add a digest helper",
        agent_name="Iris",
    )


WORK_STARTED = WorkStartedEvent(**build_fields(NotificationType.WORK_STARTED))


@pytest.fixture
def build_dispatcher() -> Callable[..., BotNotificationDispatcher]:
    return lambda poster, slack_notification_repo, composer, dag_name="demo": (
        BotNotificationDispatcher(
            poster=poster,
            slack_notification_repo=slack_notification_repo,
            channel="#dag",
            composer=composer,
            dag_name=dag_name,
        )
    )


async def test_opens_and_records_a_thread_when_the_node_has_none(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None
    composer = mocker.MagicMock(spec=NotificationComposer)
    composer.work_started.return_value = "Agent *Iris* started working on `A`"
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(WORK_STARTED)

    url, payload, _ = poster.post.call_args_list[0].args
    assert "chat.postMessage" in url
    assert "thread_ts" not in payload

    slack_notification_repo.save.assert_awaited_once()
    saved = slack_notification_repo.save.await_args.args[0]
    assert (saved.node_id, saved.thread_id) == ("A", "1700.1")


async def test_replies_in_the_thread_when_the_node_already_has_one(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = SlackNotification(
        node_id="A", channel="#dag", thread_id="1699.0", created_at=NOW
    )
    composer = mocker.MagicMock(spec=NotificationComposer)
    composer.work_started.return_value = "Agent *Iris* started working on `A`"
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(WORK_STARTED)

    assert poster.post.call_args_list[0].args[1]["thread_ts"] == "1699.0"
    slack_notification_repo.save.assert_not_awaited()


async def test_dispatch_updates_the_thread_message_when_passed_a_pull_request_opened_event(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1699.0"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = SlackNotification(
        node_id="A", channel="#dag", thread_id="1699.0", created_at=NOW
    )
    composer = mocker.MagicMock(spec=NotificationComposer)
    composer.pull_request_opened.return_value = (
        "Agent *Iris* started working on `A`\npr#42"
    )
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)
    pull_request_opened = PullRequestOpenedEvent(
        **build_fields(NotificationType.PR_OPENED), pr_details=READING
    )

    await dispatcher.dispatch(pull_request_opened)

    url, payload, _ = poster.post.call_args_list[0].args
    assert "chat.update" in url
    assert (payload["ts"], payload["text"]) == (
        "1699.0",
        "Agent *Iris* started working on `A`\npr#42",
    )
    assert "thread_ts" not in payload
    slack_notification_repo.save.assert_not_awaited()


@pytest.mark.parametrize(
    ("event", "expected_reactions"),
    [
        (
            PullRequestMergedEvent(
                **build_fields(NotificationType.MERGED), pr_details=READING
            ),
            ["tada"],
        ),
        (
            PullRequestMergedEvent(
                **build_fields(NotificationType.APPROVED_AND_MERGED),
                pr_details=READING,
            ),
            ["white_check_mark", "tada"],
        ),
        (WORK_STARTED, []),
    ],
    ids=["merged", "approved-and-merged", "still-working"],
)
async def test_marks_the_thread_when_the_event_settles_the_node(
    event: NodeEvent,
    expected_reactions: list[str],
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = SlackNotification(
        node_id="A", channel="#dag", thread_id="1699.0", created_at=NOW
    )
    composer = mocker.MagicMock(spec=NotificationComposer)
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(event)

    reactions = [
        call.args[1]["name"]
        for call in poster.post.call_args_list
        if "reactions.add" in call.args[0]
    ]
    assert reactions == expected_reactions


@pytest.mark.parametrize(
    ("event", "method_name"),
    [
        (WORK_STARTED, "work_started"),
        (
            PullRequestAdoptedEvent(
                **build_fields(NotificationType.PR_ADOPTED), pr_details=READING
            ),
            "pull_request_adopted",
        ),
        (
            PullRequestOpenedEvent(
                **build_fields(NotificationType.PR_OPENED), pr_details=READING
            ),
            "pull_request_opened",
        ),
        (
            CommentsAddedEvent(
                **build_fields(NotificationType.FEEDBACK_RECEIVED),
                pr_details=READING,
                comment_count=4,
            ),
            "comments_added",
        ),
        (
            CommentsAddressedEvent(
                **build_fields(NotificationType.FEEDBACK_ADDRESSED),
                pr_details=READING,
                comment_count=4,
            ),
            "comments_addressed",
        ),
        (
            ChecksCompletedEvent(
                **build_fields(NotificationType.CI_FAILED), pr_details=READING
            ),
            "checks_completed",
        ),
        (
            ChecksCompletedEvent(
                **build_fields(NotificationType.CI_FIXED), pr_details=READING
            ),
            "checks_completed",
        ),
        (
            MergeabilityChangedEvent(
                **build_fields(NotificationType.CONFLICTS_FOUND),
                pr_details=replace(READING, is_conflicted=True),
            ),
            "mergeability_changed",
        ),
        (
            MergeabilityChangedEvent(
                **build_fields(NotificationType.CONFLICTS_RESOLVED),
                pr_details=READING,
            ),
            "mergeability_changed",
        ),
        (
            PullRequestApprovedEvent(
                **build_fields(NotificationType.APPROVED), pr_details=READING
            ),
            "pull_request_approved",
        ),
        (
            PullRequestMergedEvent(
                **build_fields(NotificationType.MERGED), pr_details=READING
            ),
            "pull_request_merged",
        ),
        (
            PullRequestMergedEvent(
                **build_fields(NotificationType.APPROVED_AND_MERGED),
                pr_details=READING,
            ),
            "pull_request_merged",
        ),
        (
            AgentStoppedEvent(
                **build_fields(NotificationType.NEEDS_HUMAN), reason="it stopped"
            ),
            "agent_stopped",
        ),
        (
            AgentStoppedEvent(
                **build_fields(NotificationType.AGENT_FAILED), reason="it stopped"
            ),
            "agent_stopped",
        ),
        (NodeRetriedEvent(**build_fields(NotificationType.RETRIED)), "node_retried"),
        (NodeSkippedEvent(**build_fields(NotificationType.SKIPPED)), "node_skipped"),
    ],
    ids=[
        "work-started",
        "pr-adopted",
        "pr-opened",
        "feedback-received",
        "feedback-addressed",
        "ci-failed",
        "ci-fixed",
        "conflicts-found",
        "conflicts-resolved",
        "approved",
        "merged",
        "approved-and-merged",
        "needs-human",
        "agent-failed",
        "retried",
        "skipped",
    ],
)
async def test_posts_the_text_the_composer_method_returns(
    event: NodeEvent,
    method_name: str,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None
    composer = mocker.MagicMock(spec=NotificationComposer)
    getattr(composer, method_name).return_value = "the composed text"
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(event)

    getattr(composer, method_name).assert_called_once_with(event)
    assert poster.post.call_args_list[0].args[1]["text"] == "the composed text"


async def test_posts_the_message_in_a_section_block_with_a_context_line(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None
    composer = mocker.MagicMock(spec=NotificationComposer)
    composer.work_started.return_value = "Agent *Iris* started working on `A`"
    dispatcher = build_dispatcher(
        poster, slack_notification_repo, composer, dag_name="node-recovery"
    )

    await dispatcher.dispatch(WORK_STARTED)

    section, context = poster.post.call_args_list[0].args[1]["blocks"]
    assert section["text"]["text"] == "Agent *Iris* started working on `A`"
    assert context["elements"][0]["text"] == "node-recovery · A · work_started"


@pytest.mark.parametrize(
    ("event", "is_broadcast"),
    [
        (
            AgentStoppedEvent(
                **build_fields(NotificationType.NEEDS_HUMAN), reason="it stopped"
            ),
            True,
        ),
        (
            AgentStoppedEvent(
                **build_fields(NotificationType.AGENT_FAILED), reason="it stopped"
            ),
            True,
        ),
        (WORK_STARTED, False),
    ],
    ids=["needs-human", "agent-failed", "still-working"],
)
async def test_broadcasts_the_reply_to_the_channel_only_when_the_node_stops(
    event: NodeEvent,
    is_broadcast: bool,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = SlackNotification(
        node_id="A", channel="#dag", thread_id="1699.0", created_at=NOW
    )
    composer = mocker.MagicMock(spec=NotificationComposer)
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(event)

    payload = next(
        call.args[1]
        for call in poster.post.call_args_list
        if "chat.postMessage" in call.args[0]
    )
    assert payload.get("reply_broadcast", False) is is_broadcast


async def test_posts_nothing_when_the_composer_defines_no_method_for_the_event(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None
    composer = mocker.MagicMock(spec=NotificationComposer)
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    work_resumed = WorkResumedEvent(**build_fields(NotificationType.WORK_RESUMED))
    await dispatcher.dispatch(work_resumed)

    poster.post.assert_not_called()
    slack_notification_repo.save.assert_not_awaited()


async def test_records_no_thread_when_slack_refuses_the_post(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-token")
    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": False, "error": "channel_not_found"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None
    composer = mocker.MagicMock(spec=NotificationComposer)
    composer.work_started.return_value = "Agent *Iris* started working on `A`"
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(WORK_STARTED)

    slack_notification_repo.save.assert_not_awaited()


async def test_sends_nothing_when_the_run_has_no_bot_token(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    build_dispatcher: Callable[..., BotNotificationDispatcher],
) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    poster = mocker.MagicMock(spec=JsonPoster)
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    composer = mocker.MagicMock(spec=NotificationComposer)
    dispatcher = build_dispatcher(poster, slack_notification_repo, composer)

    await dispatcher.dispatch(WORK_STARTED)

    poster.post.assert_not_called()
    slack_notification_repo.save.assert_not_awaited()

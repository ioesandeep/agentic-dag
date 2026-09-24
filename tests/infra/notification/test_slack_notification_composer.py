from dataclasses import replace
from datetime import UTC, datetime

import pytest
from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.checks_completed_event import ChecksCompletedEvent
from virgo_agentic_dag.domain.events.comments_added_event import CommentsAddedEvent
from virgo_agentic_dag.domain.events.comments_addressed_event import (
    CommentsAddressedEvent,
)
from virgo_agentic_dag.domain.events.mergeability_changed_event import (
    MergeabilityChangedEvent,
)
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
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.observation.check_failure import CheckFailure
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.infra.notification.slack_notification_composer import (
    SlackNotificationComposer,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 9, tzinfo=UTC)
NODE_ID = "SIGNATURE"
TITLE = "Summarise a text"
AGENT_NAME = "Iris"
READING = PrDetails(
    number=42,
    head_sha="8bddf07abcdef",
    url="https://git.example.com/acme/thing/pull/42",
)


def test_work_started_returns_the_agent_name_and_title_when_the_title_is_nonempty() -> (
    None
):
    event = WorkStartedEvent(
        node_id=NODE_ID,
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
    )

    composer = SlackNotificationComposer()

    message = composer.work_started(event)

    assert "Iris" in message
    assert TITLE in message
    assert NODE_ID not in message


def test_work_started_returns_the_node_id_when_the_title_is_empty() -> None:
    event = WorkStartedEvent(
        node_id=NODE_ID,
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title="",
        agent_name=AGENT_NAME,
    )

    composer = SlackNotificationComposer()

    message = composer.work_started(event)

    assert NODE_ID in message


def test_pull_request_adopted_returns_the_merge_conflicts_and_the_pull_request_link() -> (
    None
):
    event = PullRequestAdoptedEvent(
        node_id=NODE_ID,
        type=NotificationType.PR_ADOPTED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=replace(
            READING, number=41, url="https://git.example.com/acme/thing/pull/41"
        ),
    )

    composer = SlackNotificationComposer()

    message = composer.pull_request_adopted(event)

    assert "was handed" in message
    assert "merge conflicts" in message
    assert "/pull/41|pr#41>" in message


def test_pull_request_adopted_includes_the_pull_request_number_in_the_message_when_the_pull_request_url_is_empty() -> (
    None
):
    event = PullRequestAdoptedEvent(
        node_id=NODE_ID,
        type=NotificationType.PR_ADOPTED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=replace(READING, number=41, url=""),
    )

    message = SlackNotificationComposer().pull_request_adopted(event)

    assert "pr#41" in message


def test_pull_request_opened_returns_slack_notification_text_when_the_event_includes_pull_request_details() -> (
    None
):
    event = PullRequestOpenedEvent(
        node_id=NODE_ID,
        type=NotificationType.PR_OPENED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=replace(READING, title="Add a digest helper"),
    )

    composer = SlackNotificationComposer()

    message = composer.pull_request_opened(event)

    assert message == (
        "Agent *Iris* started working on `Summarise a text`\n"
        "<https://git.example.com/acme/thing/pull/42>"
    )


@pytest.mark.parametrize(
    ("comment_count", "expected"),
    [(1, "1 comment was added"), (3, "3 comments were added")],
    ids=["one", "several"],
)
def test_comments_added_counts_the_comments_when_they_arrive(
    comment_count: int, expected: str
) -> None:
    event = CommentsAddedEvent(
        node_id=NODE_ID,
        type=NotificationType.FEEDBACK_RECEIVED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=READING,
        comment_count=comment_count,
    )

    composer = SlackNotificationComposer()

    message = composer.comments_added(event)

    assert expected in message


def test_comments_addressed_states_the_head_commit_when_the_pull_request_has_one() -> (
    None
):
    event = CommentsAddressedEvent(
        node_id=NODE_ID,
        type=NotificationType.FEEDBACK_ADDRESSED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=READING,
        comment_count=2,
    )

    composer = SlackNotificationComposer()

    message = composer.comments_addressed(event)

    assert "Addressed 2 comments" in message
    assert "`8bddf07a`" in message


@pytest.mark.parametrize(
    ("pr_details", "expected"),
    [
        (
            replace(
                READING,
                failures=(CheckFailure(name="release-note", conclusion="FAILURE"),),
            ),
            "has failing checks: `release-note`",
        ),
        (READING, "are green again"),
    ],
    ids=["failing", "green"],
)
def test_checks_completed_returns_the_pull_request_check_results(
    pr_details: PrDetails, expected: str
) -> None:
    event = ChecksCompletedEvent(
        node_id=NODE_ID,
        type=NotificationType.CI_FAILED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=pr_details,
    )

    composer = SlackNotificationComposer()

    message = composer.checks_completed(event)

    assert expected in message


@pytest.mark.parametrize(
    ("pr_details", "expected"),
    [
        (replace(READING, is_conflicted=True), "merge conflicts with the base branch"),
        (READING, "merges cleanly again"),
    ],
    ids=["conflicted", "mergeable"],
)
def test_mergeability_changed_returns_the_branch_mergeability(
    pr_details: PrDetails, expected: str
) -> None:
    event = MergeabilityChangedEvent(
        node_id=NODE_ID,
        type=NotificationType.CONFLICTS_FOUND,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=pr_details,
    )

    composer = SlackNotificationComposer()

    message = composer.mergeability_changed(event)

    assert expected in message


@pytest.mark.parametrize(
    ("pr_details", "expected"),
    [
        (
            replace(
                READING,
                artifacts=(
                    ReviewArtifact(
                        kind=ReviewArtifactType.REVIEW,
                        artifact_id=9,
                        author="skgiricorp",
                        body="looks good, approving",
                        created_at="2026-08-09T10:00:00Z",
                        is_approval=True,
                    ),
                ),
            ),
            "*skgiricorp* approved",
        ),
        (READING, "A reviewer approved"),
    ],
    ids=["named-approver", "no-approval-artifact"],
)
def test_pull_request_approved_returns_the_approver(
    pr_details: PrDetails, expected: str
) -> None:
    event = PullRequestApprovedEvent(
        node_id=NODE_ID,
        type=NotificationType.APPROVED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=pr_details,
    )

    composer = SlackNotificationComposer()

    message = composer.pull_request_approved(event)

    assert expected in message


def test_pull_request_merged_returns_the_merger_and_agent_names() -> None:
    event = PullRequestMergedEvent(
        node_id=NODE_ID,
        type=NotificationType.MERGED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        pr_details=replace(READING, is_merged=True, merged_by="skgiricorp"),
    )

    composer = SlackNotificationComposer()

    message = composer.pull_request_merged(event)

    assert "skgiricorp" in message
    assert "Iris" in message
    assert "wind down. Thank you!" in message


def test_agent_stopped_returns_the_node_id_the_reason_the_link_and_the_last_log_line() -> (
    None
):
    event = AgentStoppedEvent(
        node_id=NODE_ID,
        type=NotificationType.AGENT_FAILED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        reason="its session ran past its deadline and was killed",
        pr_details=READING,
        log_tail="Pushed the branch\n\nError: Reached max turns (120)\n",
    )

    composer = SlackNotificationComposer()

    message = composer.agent_stopped(event)

    assert message == (
        "`SIGNATURE` stopped on <https://git.example.com/acme/thing/pull/42|pr#42> — "
        "its session ran past its deadline and was killed\n"
        "```\nError: Reached max turns (120)\n```"
    )


def test_agent_stopped_returns_no_quote_when_the_event_has_no_log_tail() -> None:
    event = AgentStoppedEvent(
        node_id=NODE_ID,
        type=NotificationType.NEEDS_HUMAN,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        reason="its pull request was closed without merging",
        pr_details=READING,
    )

    composer = SlackNotificationComposer()

    message = composer.agent_stopped(event)

    assert message == (
        "`SIGNATURE` stopped on <https://git.example.com/acme/thing/pull/42|pr#42> — "
        "its pull request was closed without merging"
    )


def test_agent_stopped_escapes_the_slack_markup_characters_of_the_log_line() -> None:
    event = AgentStoppedEvent(
        node_id=NODE_ID,
        type=NotificationType.NEEDS_HUMAN,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
        reason="its session finished without opening a pull request",
        log_tail="post to <https://slack.com|slack> & `run` > out failed",
    )

    composer = SlackNotificationComposer()

    message = composer.agent_stopped(event)

    assert message.endswith(
        "```\npost to &lt;https://slack.com|slack&gt; &amp; run &gt; out failed\n```"
    )


def test_node_retried_returns_the_node_title() -> None:
    event = NodeRetriedEvent(
        node_id=NODE_ID,
        type=NotificationType.RETRIED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
    )

    composer = SlackNotificationComposer()

    message = composer.node_retried(event)

    assert TITLE in message
    assert "back to work" in message


def test_node_skipped_returns_the_node_title() -> None:
    event = NodeSkippedEvent(
        node_id=NODE_ID,
        type=NotificationType.SKIPPED,
        created_at=NOW,
        updated_at=NOW,
        title=TITLE,
        agent_name=AGENT_NAME,
    )

    composer = SlackNotificationComposer()

    message = composer.node_skipped(event)

    assert TITLE in message
    assert "was skipped" in message

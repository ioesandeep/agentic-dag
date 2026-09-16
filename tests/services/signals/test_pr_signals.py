import pytest
from virgo_agentic_dag.domain.notifications.notification_type import (
    NotificationType,
)
from virgo_agentic_dag.domain.observation.check_failure import CheckFailure
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.services.signals.approval_signal import ApprovalSignal
from virgo_agentic_dag.services.signals.check_signal import CheckSignal
from virgo_agentic_dag.services.signals.comment_signal import CommentSignal
from virgo_agentic_dag.services.signals.conflict_signal import ConflictSignal

pytestmark = pytest.mark.unit


def build_comment(
    author: str, created_at: str, updated_at: str = "", artifact_id: int = 1
) -> ReviewArtifact:
    return ReviewArtifact(
        kind=ReviewArtifactType.REVIEW_COMMENT,
        artifact_id=artifact_id,
        author=author,
        body="please fix this",
        created_at=created_at,
        updated_at=updated_at,
    )


def build_reading(**overrides: object) -> PrDetails:
    fields: dict[str, object] = {"number": 8, "head_sha": "abc"}
    fields.update(overrides)

    return PrDetails(**fields)  # type: ignore[arg-type]


def test_a_comment_newer_than_the_mark_wakes_the_node() -> None:
    reading = build_reading(artifacts=(build_comment("human", "2026-07-25T10:00:00Z"),))

    change = CommentSignal("bot").detect(reading, "2026-07-25T09:00:00Z")

    assert change is not None
    assert change.mark == "2026-07-25T10:00:00Z"
    assert change.notification is NotificationType.FEEDBACK_RECEIVED
    assert "human" in change.body


def test_a_comment_the_node_has_seen_is_not_reported_again() -> None:
    reading = build_reading(artifacts=(build_comment("human", "2026-07-25T10:00:00Z"),))

    assert CommentSignal("bot").detect(reading, "2026-07-25T10:00:00Z") is None


def test_the_nodes_own_comments_never_wake_it() -> None:
    reading = build_reading(artifacts=(build_comment("bot", "2026-07-25T10:00:00Z"),))

    assert CommentSignal("bot").detect(reading, "") is None


def test_an_edited_comment_reads_as_new() -> None:
    reading = build_reading(
        artifacts=(
            build_comment("human", "2026-07-25T09:00:00Z", "2026-07-25T11:00:00Z"),
        )
    )

    change = CommentSignal("bot").detect(reading, "2026-07-25T10:00:00Z")

    assert change is not None
    assert change.mark == "2026-07-25T11:00:00Z"


def test_a_new_failure_wakes_the_node_once_per_commit() -> None:
    reading = build_reading(failures=(CheckFailure(name="test", conclusion="FAILURE"),))
    signal = CheckSignal()

    first = signal.detect(reading, "")

    assert first is not None
    assert first.notification is NotificationType.CI_FAILED
    assert "`test`" in first.body
    assert signal.detect(reading, first.mark) is None


def test_a_green_pull_request_reports_no_failures() -> None:
    assert CheckSignal().detect(build_reading(), "") is None


def test_a_conflict_is_reported_once_per_commit() -> None:
    reading = build_reading(is_conflicted=True)
    signal = ConflictSignal()

    change = signal.detect(reading, "")

    assert change is not None
    assert change.mark == "abc"
    assert change.notification is NotificationType.CONFLICTS_FOUND
    assert signal.detect(reading, "abc") is None


def test_a_mergeable_pull_request_reports_no_conflict() -> None:
    assert ConflictSignal().detect(build_reading(), "") is None


def test_an_approval_is_announced_but_never_wakes_the_node() -> None:
    change = ApprovalSignal().detect(build_reading(is_approved=True), "")

    assert change is not None
    assert change.wakes_node is False
    assert change.notification is NotificationType.APPROVED


def test_an_approval_is_announced_once_per_commit() -> None:
    reading = build_reading(is_approved=True)
    signal = ApprovalSignal()

    first = signal.detect(reading, "")

    assert first is not None
    assert signal.detect(reading, first.mark) is None


def test_an_unapproved_pull_request_announces_nothing() -> None:
    assert ApprovalSignal().detect(build_reading(), "") is None


def build_review(is_approval: bool) -> ReviewArtifact:
    return ReviewArtifact(
        kind=ReviewArtifactType.REVIEW,
        artifact_id=9,
        author="human",
        body="looks good, approving",
        created_at="2026-07-25T10:00:00Z",
        is_approval=is_approval,
    )


def test_an_approval_message_is_not_work_for_the_node() -> None:
    reading = build_reading(artifacts=(build_review(is_approval=True),))

    assert CommentSignal("bot").detect(reading, "") is None


def test_a_change_request_message_is_still_work_for_the_node() -> None:
    reading = build_reading(artifacts=(build_review(is_approval=False),))

    assert CommentSignal("bot").detect(reading, "") is not None

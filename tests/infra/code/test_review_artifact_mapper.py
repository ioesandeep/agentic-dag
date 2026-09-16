import pytest
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.infra.code.review_artifact_mapper import ReviewArtifactMapper

pytestmark = pytest.mark.unit


def test_maps_a_comment_with_its_author_and_body():
    entries = [
        {
            "id": 5,
            "user": {"login": "maintainer"},
            "body": " please fix ",
            "created_at": "2026-07-25T00:00:00Z",
        }
    ]

    artifacts = ReviewArtifactMapper().get_all(
        ReviewArtifactType.ISSUE_COMMENT, entries
    )

    assert artifacts[0].author == "maintainer"
    assert artifacts[0].body == "please fix"
    assert artifacts[0].artifact_id == 5


def test_an_empty_comment_is_not_feedback():
    entries = [{"id": 5, "user": {"login": "m"}, "body": "   "}]

    assert (
        ReviewArtifactMapper().get_all(ReviewArtifactType.ISSUE_COMMENT, entries) == ()
    )


def test_an_approval_with_no_body_is_not_feedback():
    entries = [{"id": 5, "user": {"login": "m"}, "body": "", "state": "APPROVED"}]

    assert ReviewArtifactMapper().get_all(ReviewArtifactType.REVIEW, entries) == ()


def test_a_changes_requested_review_is_feedback_even_when_empty():
    entries = [
        {"id": 5, "user": {"login": "m"}, "body": "", "state": "CHANGES_REQUESTED"}
    ]

    assert len(ReviewArtifactMapper().get_all(ReviewArtifactType.REVIEW, entries)) == 1


def test_a_review_submission_time_is_its_creation_time():
    entries = [
        {
            "id": 5,
            "user": {"login": "m"},
            "body": "looks off",
            "submitted_at": "2026-07-25T09:00:00Z",
        }
    ]

    artifacts = ReviewArtifactMapper().get_all(ReviewArtifactType.REVIEW, entries)

    assert artifacts[0].created_at == "2026-07-25T09:00:00Z"

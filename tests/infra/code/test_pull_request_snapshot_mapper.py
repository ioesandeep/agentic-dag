import pytest
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.infra.code.pull_request_snapshot_mapper import (
    PullRequestSnapshotMapper,
)

pytestmark = pytest.mark.unit

COMPLETE_PAYLOAD = {
    "state": "OPEN",
    "headRefOid": "abc123",
    "baseRefName": "develop",
    "mergeable": "MERGEABLE",
    "reviewDecision": "APPROVED",
    "statusCheckRollup": [{"name": "build", "conclusion": "SUCCESS"}],
    "mergeCommit": None,
}


def test_reads_an_open_pull_request():
    snapshot = PullRequestSnapshotMapper().get_snapshot(COMPLETE_PAYLOAD)

    assert snapshot.state is PullRequestState.OPEN
    assert snapshot.head_sha == "abc123"
    assert snapshot.base_branch == "develop"
    assert snapshot.is_complete is True


def test_reads_a_merged_pull_request_with_its_merge_commit():
    payload = {
        **COMPLETE_PAYLOAD,
        "state": "MERGED",
        "mergeCommit": {"oid": "deadbeef"},
    }

    snapshot = PullRequestSnapshotMapper().get_snapshot(payload)

    assert snapshot.state is PullRequestState.MERGED
    assert snapshot.merge_commit_sha == "deadbeef"


def test_conflicting_pull_request_is_not_mergeable():
    payload = {**COMPLETE_PAYLOAD, "mergeable": "CONFLICTING"}

    assert PullRequestSnapshotMapper().get_snapshot(payload).is_mergeable is False


def test_unknown_mergeability_on_an_open_pull_request_is_incomplete():
    payload = {**COMPLETE_PAYLOAD, "mergeable": "UNKNOWN"}

    snapshot = PullRequestSnapshotMapper().get_snapshot(payload)

    assert snapshot.is_complete is False


def test_unknown_mergeability_on_a_merged_pull_request_is_complete():
    payload = {
        **COMPLETE_PAYLOAD,
        "state": "MERGED",
        "mergeable": "UNKNOWN",
        "mergeCommit": {"oid": "deadbeef"},
    }

    snapshot = PullRequestSnapshotMapper().get_snapshot(payload)

    assert snapshot.is_complete is True
    assert snapshot.state is PullRequestState.MERGED


def test_unknown_mergeability_on_a_closed_pull_request_is_complete():
    payload = {**COMPLETE_PAYLOAD, "state": "CLOSED", "mergeable": "UNKNOWN"}

    assert PullRequestSnapshotMapper().get_snapshot(payload).is_complete is True


def test_missing_field_marks_the_reading_incomplete():
    payload = {k: v for k, v in COMPLETE_PAYLOAD.items() if k != "statusCheckRollup"}

    assert PullRequestSnapshotMapper().get_snapshot(payload).is_complete is False


def test_changes_requested_is_unhandled_feedback():
    payload = {**COMPLETE_PAYLOAD, "reviewDecision": "CHANGES_REQUESTED"}

    assert PullRequestSnapshotMapper().get_snapshot(payload).has_changes_requested


def test_failed_checks_are_collected_by_name():
    payload = {
        **COMPLETE_PAYLOAD,
        "statusCheckRollup": [
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "typecheck", "conclusion": "FAILURE"},
            {"name": "e2e", "conclusion": "TIMED_OUT"},
        ],
    }

    snapshot = PullRequestSnapshotMapper().get_snapshot(payload)

    assert [failure.name for failure in snapshot.failures] == ["typecheck", "e2e"]


def test_the_merge_actor_is_read():
    snapshot = PullRequestSnapshotMapper().get_snapshot(
        {
            "state": "MERGED",
            "headRefOid": "abc123",
            "baseRefName": "develop",
            "mergeable": "MERGEABLE",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [],
            "mergedBy": {"login": "sandeep"},
        }
    )

    assert snapshot.merged_by == "sandeep"


def test_an_absent_merge_actor_reads_as_empty():
    snapshot = PullRequestSnapshotMapper().get_snapshot(
        {
            "state": "OPEN",
            "headRefOid": "abc123",
            "baseRefName": "develop",
            "mergeable": "MERGEABLE",
            "reviewDecision": "",
            "statusCheckRollup": [],
        }
    )

    assert snapshot.merged_by == ""

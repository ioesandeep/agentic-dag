import json

import pytest
from virgo_agentic_dag.server.pr_topic_extractor import PrTopicExtractor

pytestmark = pytest.mark.unit

REPOSITORY = {"full_name": "acme/virgo"}


def build_body(payload: dict[str, object]) -> bytes:
    return json.dumps({"repository": REPOSITORY, **payload}).encode()


@pytest.mark.parametrize(
    "event",
    ["pull_request", "pull_request_review", "pull_request_review_comment"],
)
def test_names_the_pull_request_the_delivery_is_about(event: str) -> None:
    body = build_body({"pull_request": {"number": 12}})

    assert PrTopicExtractor().get_topics(event, body) == ["acme/virgo#12"]


def test_names_the_pull_request_a_comment_landed_on() -> None:
    body = build_body({"issue": {"number": 7, "pull_request": {}}})

    assert PrTopicExtractor().get_topics("issue_comment", body) == ["acme/virgo#7"]


def test_names_nothing_for_a_comment_on_a_plain_issue() -> None:
    body = build_body({"issue": {"number": 7}})

    assert PrTopicExtractor().get_topics("issue_comment", body) == []


@pytest.mark.parametrize("event", ["check_suite", "check_run"])
def test_names_every_pull_request_a_check_reports_on(event: str) -> None:
    body = build_body(
        {event: {"pull_requests": [{"number": 3}, {"number": 4}, {"number": 3}]}}
    )

    assert PrTopicExtractor().get_topics(event, body) == [
        "acme/virgo#3",
        "acme/virgo#4",
    ]


def test_names_nothing_for_an_event_without_a_pull_request() -> None:
    body = build_body({"ref": "refs/heads/main"})

    assert PrTopicExtractor().get_topics("push", body) == []


def test_names_nothing_when_the_body_is_not_json() -> None:
    assert PrTopicExtractor().get_topics("pull_request", b"not json") == []


def test_names_nothing_when_the_repository_is_missing() -> None:
    body = json.dumps({"pull_request": {"number": 12}}).encode()

    assert PrTopicExtractor().get_topics("pull_request", body) == []

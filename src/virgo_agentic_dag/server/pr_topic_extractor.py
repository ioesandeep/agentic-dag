"""Reading which pull requests a webhook delivery is about, so events can be routed."""

from __future__ import annotations

import json
from typing import Any

_PULL_REQUEST_EVENTS = (
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
)
_CHECK_EVENTS = ("check_suite", "check_run")


class PrTopicExtractor:
    """Names the pull requests a delivery touches, as `owner/repo#number` topics."""

    def get_topics(self, event: str, body: bytes) -> list[str]:
        """Return the delivery's pull request topics, empty when it names none."""
        data = self._parse(body)
        if data is None:
            return []

        if event in _PULL_REQUEST_EVENTS:
            return self._from_pull_request(data)

        if event == "issue_comment":
            return self._from_issue_comment(data)

        if event in _CHECK_EVENTS:
            return self._from_checks(event, data)

        return []

    def _parse(self, body: bytes) -> dict[str, Any] | None:
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        return data

    def _from_pull_request(self, data: dict[str, Any]) -> list[str]:
        pull_request = data.get("pull_request")
        if not isinstance(pull_request, dict):
            return []

        return self._build_topics(data, [pull_request.get("number")])

    def _from_issue_comment(self, data: dict[str, Any]) -> list[str]:
        issue = data.get("issue")
        if not isinstance(issue, dict) or issue.get("pull_request") is None:
            return []

        return self._build_topics(data, [issue.get("number")])

    def _from_checks(self, event: str, data: dict[str, Any]) -> list[str]:
        container = data.get(event)
        if not isinstance(container, dict):
            return []

        pull_requests = container.get("pull_requests")
        if not isinstance(pull_requests, list):
            return []

        numbers = [
            pull_request.get("number")
            for pull_request in pull_requests
            if isinstance(pull_request, dict)
        ]

        return self._build_topics(data, numbers)

    def _build_topics(self, data: dict[str, Any], numbers: list[Any]) -> list[str]:
        repository = data.get("repository")
        if not isinstance(repository, dict):
            return []

        full_name = repository.get("full_name")
        if not isinstance(full_name, str) or not full_name:
            return []

        topics = [
            f"{full_name}#{number}" for number in numbers if isinstance(number, int)
        ]

        return list(dict.fromkeys(topics))

import os
import time
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.infra.agent.claude_usage_limit_reader import (
    ClaudeUsageLimitReader,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("log_tail", "ended_at", "expected_reset"),
    [
        (
            "You've hit your session limit · resets 4:20pm (America/Los_Angeles)\n",
            datetime(2026, 9, 26, 22, tzinfo=UTC),
            datetime(2026, 9, 26, 23, 20, tzinfo=UTC),
        ),
        (
            "You've hit your session limit · resets 4:20pm (America/Los_Angeles)",
            datetime(2026, 9, 26, 23, 20, tzinfo=UTC),
            datetime(2026, 9, 27, 23, 20, tzinfo=UTC),
        ),
        (
            "You've hit your weekly limit · resets Sep 29, 7pm (America/Los_Angeles)",
            datetime(2026, 9, 26, 22, tzinfo=UTC),
            datetime(2026, 9, 30, 2, tzinfo=UTC),
        ),
        (
            "You've hit your weekly limit · resets Jan 2, 2027, 7pm (UTC) · progress saved",
            datetime(2026, 12, 31, 22, tzinfo=UTC),
            datetime(2027, 1, 2, 19, tzinfo=UTC),
        ),
        (
            "You've hit your weekly limit · resets Jan 2, 7pm (UTC)",
            datetime(2026, 12, 31, 22, tzinfo=UTC),
            datetime(2027, 1, 2, 19, tzinfo=UTC),
        ),
        (
            "You've hit your session limit · resets 1:30am (America/Los_Angeles)",
            datetime(2026, 11, 1, 8, 45, tzinfo=UTC),
            datetime(2026, 11, 1, 9, 30, tzinfo=UTC),
        ),
    ],
)
def test_reader_returns_reset_time_when_claude_ends_on_a_limit(
    log_tail: str, ended_at: datetime, expected_reset: datetime
) -> None:
    reader = ClaudeUsageLimitReader()

    reset_time = reader.get_reset_time(log_tail, ended_at)

    assert reset_time == expected_reset


def test_reader_uses_host_zone_when_claude_omits_the_zone(
    mocker: MockerFixture,
) -> None:
    reader = ClaudeUsageLimitReader()
    ended_at = datetime(2026, 9, 26, 22, tzinfo=UTC)

    environment_patch = mocker.patch.dict(os.environ, {"TZ": "Asia/Kathmandu"})
    time.tzset()
    try:
        reset_time = reader.get_reset_time(
            "You've hit your session limit · resets 4:20pm", ended_at
        )

    finally:
        mocker.stop(environment_patch)
        time.tzset()

    assert reset_time == datetime(2026, 9, 27, 10, 35, tzinfo=UTC)


@pytest.mark.parametrize(
    "log_tail",
    [
        "Work completed.\n",
        "You've hit your weekly limit",
        "You've hit your session limit · resets invalid (UTC)",
        "You've hit your session limit · resets 4:20pm (Invalid/Zone)",
        "You've hit your session limit · resets 4:20pm (UTC)\nWork completed.",
        "",
    ],
)
def test_reader_returns_none_when_claude_has_no_terminal_reset_time(
    log_tail: str,
) -> None:
    reader = ClaudeUsageLimitReader()
    ended_at = datetime(2026, 9, 26, 22, tzinfo=UTC)

    reset_time = reader.get_reset_time(log_tail, ended_at)

    assert reset_time is None

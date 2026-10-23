import json
import os
import time
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.infra.agent.codex_usage_limit_reader import CodexUsageLimitReader

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("event_type", "message", "host_zone", "ended_at", "expected_reset"),
    [
        (
            "error",
            "You’ve hit your usage limit. Try again at 4:20 PM.",
            "Asia/Kathmandu",
            datetime(2026, 9, 26, 22, tzinfo=UTC),
            datetime(2026, 9, 27, 10, 35, tzinfo=UTC),
        ),
        (
            "turn.failed",
            "You’ve hit your usage limit. Visit https://chatgpt.com/settings/usage "
            "to purchase more credits or try again at Sep 29th, 2026 4:20 PM.",
            "Asia/Kathmandu",
            datetime(2026, 9, 26, 22, tzinfo=UTC),
            datetime(2026, 9, 29, 10, 35, tzinfo=UTC),
        ),
        (
            "turn.failed",
            "You’ve hit your usage limit. Try again at 1:30 AM.",
            "America/Los_Angeles",
            datetime(2026, 11, 1, 8, 45, tzinfo=UTC),
            datetime(2026, 11, 1, 9, 30, tzinfo=UTC),
        ),
    ],
)
def test_reader_returns_reset_time_when_codex_ends_on_a_usage_limit(
    event_type: str,
    message: str,
    host_zone: str,
    ended_at: datetime,
    expected_reset: datetime,
    mocker: MockerFixture,
) -> None:
    event = {"type": event_type, "message": message}
    if event_type == "turn.failed":
        event = {"type": event_type, "error": {"message": message}}

    log_tail = json.dumps(event) + "\n"
    reader = CodexUsageLimitReader()

    environment_patch = mocker.patch.dict(os.environ, {"TZ": host_zone})
    time.tzset()
    try:
        reset_time = reader.get_reset_time(log_tail, ended_at)

    finally:
        mocker.stop(environment_patch)
        time.tzset()

    assert reset_time == expected_reset


@pytest.mark.parametrize(
    "log_tail",
    [
        '{"type":"turn.failed","error":{"message":"Connection failed"}}',
        '{"type":"error","message":"You’ve hit your usage limit. Try again later."}',
        '{"type":"error","message":"You’ve hit your usage limit. Try again at invalid."}',
        '{"type":"item.completed","item":{"text":"You’ve hit your usage limit. Try again at 4:20 PM."}}',
        '{"type":"error","message":"You’ve hit your usage limit. Try again at 4:20 PM."}\n'
        '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":1}}',
        "not json",
    ],
)
def test_reader_returns_none_when_codex_has_no_terminal_reset_time(
    log_tail: str,
) -> None:
    reader = CodexUsageLimitReader()
    ended_at = datetime(2026, 9, 26, 22, tzinfo=UTC)

    reset_time = reader.get_reset_time(log_tail, ended_at)

    assert reset_time is None

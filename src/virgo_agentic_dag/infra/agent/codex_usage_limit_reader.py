import json
import re
from datetime import UTC, datetime, timedelta
from typing import cast

from virgo_agentic_dag.domain.infra.agent.usage_limit_reader import UsageLimitReader


class CodexUsageLimitReader(UsageLimitReader):
    """Identifies Codex usage-limit reset times."""

    def get_reset_time(self, log_tail: str, ended_at: datetime) -> datetime | None:
        """Return the reset time when Codex ends on a usage-limit error."""
        log_lines = log_tail.rstrip().splitlines()
        if not log_lines:
            return None

        try:
            event = json.loads(log_lines[-1])
        except json.JSONDecodeError:
            return None

        is_event = isinstance(event, dict)
        if not is_event:
            return None

        event_type = event.get("type")
        if event_type == "turn.failed":
            event = event.get("error")
        elif event_type != "error":
            return None

        is_error_event = isinstance(event, dict)
        message = event.get("message") if is_error_event else None
        is_message = isinstance(message, str)
        if not is_message:
            return None

        message = cast(str, message)

        return self._get_reset_time(message, ended_at)

    def _get_reset_time(self, message: str, ended_at: datetime) -> datetime | None:
        limit_match = re.fullmatch(
            r"You['’]ve hit your usage limit.*?[Tt]ry again at (?P<reset>.+)\.",
            message,
        )

        if limit_match is None:
            return None

        reset_text = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", limit_match["reset"])
        for time_format in ["%I:%M %p", "%b %d, %Y %I:%M %p", "%b %d, %Y, %I:%M %p"]:
            try:
                reset_time = datetime.strptime(reset_text, time_format)
            except ValueError:
                continue

            if "%Y" not in time_format:
                local_end = ended_at.astimezone()
                reset_time = reset_time.replace(
                    year=local_end.year, month=local_end.month, day=local_end.day
                )

            return self._get_next_reset_time(reset_time, time_format, ended_at)

        return None

    def _get_next_reset_time(
        self, reset_time: datetime, time_format: str, ended_at: datetime
    ) -> datetime:
        reset_candidates = [
            reset_time.replace(fold=fold).astimezone(UTC) for fold in [0, 1]
        ]

        future_candidates = [
            candidate for candidate in reset_candidates if candidate > ended_at
        ]

        if future_candidates:
            return min(future_candidates)

        if "%Y" in time_format:
            return reset_candidates[0]

        next_reset_time = reset_time + timedelta(days=1)

        return self._get_next_reset_time(next_reset_time, time_format, ended_at)

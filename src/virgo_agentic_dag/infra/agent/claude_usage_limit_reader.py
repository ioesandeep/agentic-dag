import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from virgo_agentic_dag.domain.infra.agent.usage_limit_reader import UsageLimitReader


class ClaudeUsageLimitReader(UsageLimitReader):
    """Identifies Claude usage-limit reset times."""

    def get_reset_time(self, log_tail: str, ended_at: datetime) -> datetime | None:
        """Return the reset time when Claude ends on a session or weekly limit."""
        log_lines = log_tail.rstrip().splitlines()
        if not log_lines:
            return None

        final_line = log_lines[-1].strip()
        limit_match = re.fullmatch(
            r"You've hit your (?:session|weekly) limit · resets "
            r"(?P<reset>[^()·]+?)(?: \((?P<zone>[^)]+)\))?(?: · .*)?",
            final_line,
        )

        if limit_match is None:
            return None

        zone_name = limit_match["zone"]
        try:
            zone = ZoneInfo(zone_name) if zone_name else None
        except ZoneInfoNotFoundError:
            return None

        reset_text = limit_match["reset"].strip()

        return self._get_reset_time(reset_text, zone, ended_at)

    def _get_reset_time(
        self, reset_text: str, zone: ZoneInfo | None, ended_at: datetime
    ) -> datetime | None:
        local_end = ended_at.astimezone(zone)
        for time_format in [
            "%I:%M%p",
            "%I%p",
            "%b %d, %I:%M%p",
            "%b %d, %I%p",
            "%b %d, %Y, %I:%M%p",
            "%b %d, %Y, %I%p",
        ]:
            dated_text = reset_text
            dated_format = time_format
            if "%Y" not in time_format:
                dated_text = f"{reset_text} {local_end.year}"
                dated_format = f"{time_format} %Y"

            try:
                reset_time = datetime.strptime(dated_text, dated_format)
            except ValueError:
                continue

            if "%b" not in time_format:
                reset_time = reset_time.replace(
                    month=local_end.month, day=local_end.day
                )

            reset_time = reset_time.replace(tzinfo=zone)

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

        if "%b" in time_format:
            next_reset_time = reset_time.replace(year=reset_time.year + 1)
        else:
            next_reset_time = reset_time + timedelta(days=1)

        return self._get_next_reset_time(next_reset_time, time_format, ended_at)

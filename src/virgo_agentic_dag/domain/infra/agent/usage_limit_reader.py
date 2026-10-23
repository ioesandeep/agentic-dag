from abc import ABC, abstractmethod
from datetime import datetime


class UsageLimitReader(ABC):
    """Identifies usage-limit reset times in session output."""

    @abstractmethod
    def get_reset_time(self, log_tail: str, ended_at: datetime) -> datetime | None:
        """Return the reset time when a usage limit ends the session."""

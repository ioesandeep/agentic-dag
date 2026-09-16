"""The production Sleeper, pausing the calling thread for real time."""

from __future__ import annotations

import time

from virgo_agentic_dag.domain.infra.host.sleeper import Sleeper


class SystemSleeper(Sleeper):
    """Pauses the calling thread using the host clock."""

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

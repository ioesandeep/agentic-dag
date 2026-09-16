"""Posts JSON over HTTP with the standard library, so the package keeps no runtime dependency."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster

logger = logging.getLogger(__name__)


class UrllibJsonPoster(JsonPoster):
    """Posts JSON through urllib, logging delivery failures instead of raising them."""

    def __init__(self, timeout_seconds: int = 10) -> None:
        self._timeout_seconds = timeout_seconds

    def post(
        self, url: str, payload: Mapping[str, Any], token: str
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(dict(payload)).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                decoded: Any = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            logger.warning("notification post to %s failed: %s", url, error)

            return {}

        if not isinstance(decoded, dict):
            return {}

        return decoded

"""The port for posting a JSON document to an HTTP endpoint."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class JsonPoster(ABC):
    """Posts a JSON body and returns the decoded reply, so sinks never speak HTTP themselves."""

    @abstractmethod
    def post(
        self, url: str, payload: Mapping[str, Any], token: str
    ) -> Mapping[str, Any]:
        """Post the payload as JSON and return the decoded response, empty when it failed."""

"""Verification of GitHub webhook HMAC signatures."""

from __future__ import annotations

import hashlib
import hmac


class WebhookSignatureVerifier:
    """Checks that a webhook body carries a valid X-Hub-Signature-256 header."""

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def is_valid(self, signature_header: str, body: bytes) -> bool:
        """Return whether the header's digest matches the body under the shared secret."""
        if not signature_header.startswith("sha256="):
            return False

        expected = hmac.new(self._secret, body, hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)

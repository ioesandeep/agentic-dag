import hashlib
import hmac

import pytest
from virgo_agentic_dag.server.webhook_signature_verifier import WebhookSignatureVerifier

pytestmark = pytest.mark.unit


def sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    return f"sha256={digest}"


def test_accepts_matching_signature() -> None:
    verifier = WebhookSignatureVerifier("secret")

    assert verifier.is_valid(sign("secret", b"payload"), b"payload")


def test_rejects_wrong_secret() -> None:
    verifier = WebhookSignatureVerifier("secret")

    assert not verifier.is_valid(sign("other", b"payload"), b"payload")


def test_rejects_header_without_prefix() -> None:
    verifier = WebhookSignatureVerifier("secret")

    assert not verifier.is_valid("bad-header", b"payload")

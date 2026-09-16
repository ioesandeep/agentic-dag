import hashlib
import hmac
import http.client
import json
import threading
import time
from collections.abc import Iterator

import pytest
from virgo_agentic_dag.server.pr_topic_extractor import PrTopicExtractor
from virgo_agentic_dag.server.sse_hub import SseHub
from virgo_agentic_dag.server.webhook_signature_verifier import WebhookSignatureVerifier
from virgo_agentic_dag.server.webhook_sse_server import WebhookSseServer

pytestmark = pytest.mark.integration

SECRET = "test-secret"


@pytest.fixture
def server() -> Iterator[WebhookSseServer]:
    verifier = WebhookSignatureVerifier(SECRET)
    bridge = WebhookSseServer(("127.0.0.1", 0), SseHub(), verifier, PrTopicExtractor())
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()

    yield bridge

    bridge.shutdown()
    bridge.server_close()


def build_pull_request_body(number: int) -> bytes:
    return json.dumps(
        {
            "repository": {"full_name": "acme/virgo"},
            "pull_request": {"number": number},
        }
    ).encode()


def sign(body: bytes) -> str:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

    return f"sha256={digest}"


def post_webhook(
    port: int, body: bytes, signature: str, event: str = "pull_request"
) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"X-Hub-Signature-256": signature, "X-GitHub-Event": event}
    connection.request("POST", "/webhook", body, headers)
    status = connection.getresponse().status
    connection.close()

    return status


def wait_for_subscription(hub: SseHub) -> None:
    deadline = time.monotonic() + 5
    while hub.count_subscribers() == 0:
        if time.monotonic() > deadline:
            raise AssertionError("subscriber never registered")

        time.sleep(0.01)


def test_rejects_a_subscriber_that_names_no_topics(server: WebhookSseServer) -> None:
    subscriber = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    subscriber.request("GET", "/events")

    assert subscriber.getresponse().status == 400

    subscriber.close()


def test_scoped_subscriber_hears_only_its_own_pull_request(
    server: WebhookSseServer,
) -> None:
    subscriber = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    subscriber.request("GET", "/events?topics=acme/virgo%2312")
    response = subscriber.getresponse()
    wait_for_subscription(server.hub)
    elsewhere = build_pull_request_body(99)
    watched = build_pull_request_body(12)

    leaked = post_webhook(
        server.server_port, elsewhere, sign(elsewhere), event="pull_request_review"
    )
    assert leaked == 204
    assert post_webhook(server.server_port, watched, sign(watched)) == 204

    assert response.readline() == b"data: pull_request\n"
    assert response.readline() == b"\n"

    subscriber.close()


def test_rejects_invalid_signature(server: WebhookSseServer) -> None:
    status = post_webhook(server.server_port, b"{}", "sha256=bad")

    assert status == 401


def test_rejects_unknown_paths(server: WebhookSseServer) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.request("GET", "/nope")
    status = connection.getresponse().status
    connection.close()

    assert status == 404


def test_health_endpoint_answers_ok(server: WebhookSseServer) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.request("GET", "/healthz")
    response = connection.getresponse()

    assert response.status == 200
    assert response.read() == b"ok\n"

    connection.close()

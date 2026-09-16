import threading
from collections.abc import Iterator

import pytest
from virgo_agentic_dag.infra.streaming.sse_health_check import SseHealthCheck
from virgo_agentic_dag.server.pr_topic_extractor import PrTopicExtractor
from virgo_agentic_dag.server.sse_hub import SseHub
from virgo_agentic_dag.server.webhook_signature_verifier import WebhookSignatureVerifier
from virgo_agentic_dag.server.webhook_sse_server import WebhookSseServer

pytestmark = pytest.mark.integration

DEAD_SSE_URL = "http://127.0.0.1:9/events"


@pytest.fixture
def server() -> Iterator[WebhookSseServer]:
    verifier = WebhookSignatureVerifier("health-secret")
    bridge = WebhookSseServer(("127.0.0.1", 0), SseHub(), verifier, PrTopicExtractor())
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()

    yield bridge

    bridge.shutdown()
    bridge.server_close()


async def test_health_check_reports_alive_when_the_sse_server_answers(
    server: WebhookSseServer,
) -> None:
    health_check = SseHealthCheck(timeout_seconds=5)

    health = await health_check.check(f"http://127.0.0.1:{server.server_port}/events")

    assert health.is_alive is True


@pytest.mark.parametrize(
    "stream_path", ["/events", "/events?topics=acme/virgo%2312", "/"]
)
async def test_health_check_asks_the_route_derived_from_the_stream_url(
    stream_path: str,
) -> None:
    health_check = SseHealthCheck(timeout_seconds=1)

    health = await health_check.check(f"http://127.0.0.1:9{stream_path}")

    assert health.url == "http://127.0.0.1:9/healthz"


async def test_health_check_reports_not_alive_when_nothing_answers() -> None:
    health_check = SseHealthCheck(timeout_seconds=1)

    health = await health_check.check(DEAD_SSE_URL)

    assert health.is_alive is False

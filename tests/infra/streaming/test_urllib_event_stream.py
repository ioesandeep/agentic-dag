import hashlib
import hmac
import http.client
import json
import queue
import socket
import threading
import time
from collections.abc import Iterator

import pytest
from virgo_agentic_dag.domain.exceptions.platform.stream_error import StreamError
from virgo_agentic_dag.infra.streaming.urllib_event_stream import UrllibEventStream
from virgo_agentic_dag.server.pr_topic_extractor import PrTopicExtractor
from virgo_agentic_dag.server.sse_hub import SseHub
from virgo_agentic_dag.server.webhook_signature_verifier import WebhookSignatureVerifier
from virgo_agentic_dag.server.webhook_sse_server import WebhookSseServer

pytestmark = pytest.mark.integration

SECRET = "stream-secret"


class ParkedSseServer:
    """Sends the SSE headers and nothing after them, so a client parks in its read."""

    def __init__(self) -> None:
        self._listener = socket.create_server(("127.0.0.1", 0))
        self._connections: queue.Queue[socket.socket] = queue.Queue()
        self._thread = threading.Thread(target=self._accept, daemon=True)

    @property
    def port(self) -> int:
        """Return the port the stub is listening on."""
        return int(self._listener.getsockname()[1])

    def start(self) -> None:
        """Begin accepting connections in the background."""
        self._thread.start()

    def get_connection(self) -> socket.socket:
        """Return the server side of the next connection a client opens."""
        return self._connections.get(timeout=5)

    def close(self) -> None:
        """Stop listening, which ends the accept loop."""
        self._listener.close()

    def _accept(self) -> None:
        while True:
            try:
                connection, _ = self._listener.accept()
            except OSError:
                return

            connection.recv(65536)
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n"
            )
            self._connections.put(connection)


@pytest.fixture
def parked_server() -> Iterator[ParkedSseServer]:
    stub = ParkedSseServer()
    stub.start()

    yield stub

    stub.close()


@pytest.fixture
def server() -> Iterator[WebhookSseServer]:
    verifier = WebhookSignatureVerifier(SECRET)
    bridge = WebhookSseServer(("127.0.0.1", 0), SseHub(), verifier, PrTopicExtractor())
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()

    yield bridge

    bridge.shutdown()
    bridge.server_close()


def build_body() -> bytes:
    return json.dumps(
        {"repository": {"full_name": "acme/virgo"}, "pull_request": {"number": 12}}
    ).encode()


def sign(body: bytes) -> str:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

    return f"sha256={digest}"


def post_webhook(port: int, body: bytes) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"X-Hub-Signature-256": sign(body), "X-GitHub-Event": "pull_request"}
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


def test_subscribe_yields_payload_published_by_server(server: WebhookSseServer) -> None:
    stream = UrllibEventStream(
        f"http://127.0.0.1:{server.server_port}/events?topics=acme/virgo%2312"
    )
    received: queue.Queue[str] = queue.Queue()

    def get_first_payload() -> None:
        for payload in stream.subscribe():
            received.put(payload)

            return

    reader = threading.Thread(target=get_first_payload, daemon=True)
    reader.start()
    wait_for_subscription(server.hub)

    assert post_webhook(server.server_port, build_body()) == 204
    assert received.get(timeout=5) == "pull_request"


def test_subscribe_raises_stream_error_when_server_is_unreachable() -> None:
    stream = UrllibEventStream("http://127.0.0.1:9/events")

    with pytest.raises(StreamError):
        next(stream.subscribe())


def start_parked_reader(
    stream: UrllibEventStream, stub: ParkedSseServer
) -> tuple[queue.Queue[str], socket.socket]:
    outcome: queue.Queue[str] = queue.Queue()

    def read_until_it_ends() -> None:
        try:
            for _ in stream.subscribe():
                pass
        except StreamError:
            pass

        outcome.put("ended")

    threading.Thread(target=read_until_it_ends, daemon=True).start()

    return outcome, stub.get_connection()


def test_close_ends_a_parked_read_and_shuts_the_socket(
    parked_server: ParkedSseServer,
) -> None:
    stream = UrllibEventStream(f"http://127.0.0.1:{parked_server.port}/events")
    outcome, connection = start_parked_reader(stream, parked_server)

    stream.close()

    assert outcome.get(timeout=5) == "ended"
    assert connection.recv(64) == b""


def test_close_tolerates_a_second_call_while_a_read_is_parked(
    parked_server: ParkedSseServer,
) -> None:
    stream = UrllibEventStream(f"http://127.0.0.1:{parked_server.port}/events")
    outcome, connection = start_parked_reader(stream, parked_server)

    stream.close()
    stream.close()

    assert outcome.get(timeout=5) == "ended"
    assert connection.recv(64) == b""


def test_subscribe_raises_stream_error_after_close(
    parked_server: ParkedSseServer,
) -> None:
    stream = UrllibEventStream(f"http://127.0.0.1:{parked_server.port}/events")

    stream.close()

    with pytest.raises(StreamError):
        next(stream.subscribe())

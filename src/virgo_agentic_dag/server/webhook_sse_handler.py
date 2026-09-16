"""The HTTP handler that turns verified GitHub webhooks into server-sent events."""

from __future__ import annotations

import logging
import queue
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from virgo_agentic_dag.server.webhook_sse_server import WebhookSseServer

logger = logging.getLogger(__name__)

KEEP_ALIVE_SECONDS = 15.0

TOPICS_PARAMETER = "topics"


class WebhookSseHandler(BaseHTTPRequestHandler):
    """Accepts webhook deliveries on /webhook and streams pokes to /events subscribers."""

    server: WebhookSseServer

    def do_POST(self) -> None:
        """Acknowledge one verified webhook delivery, then fan it out to subscribers."""
        if self.path != "/webhook":
            self.send_error(HTTPStatus.NOT_FOUND)

            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        signature = str(self.headers.get("X-Hub-Signature-256", ""))
        if not self.server.verifier.is_valid(signature, body):
            self.send_error(HTTPStatus.UNAUTHORIZED)

            return

        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

        event = str(self.headers.get("X-GitHub-Event", "unknown"))
        topics = self.server.extractor.get_topics(event, body)
        self.server.hub.publish(event, topics)
        logger.info(
            "published %s for %s to %d subscribers",
            event,
            topics or "no topic",
            self.server.hub.count_subscribers(),
        )

    def do_GET(self) -> None:
        """Serve the health check or hold the connection open as an SSE stream."""
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_health()

            return

        if parsed.path != "/events":
            self.send_error(HTTPStatus.NOT_FOUND)

            return

        topics = self._get_topics(parsed.query)
        if not topics:
            self.send_error(HTTPStatus.BAD_REQUEST, "name the topics to subscribe to")

            return

        self._stream_events(topics)

    def log_message(self, format: str, *args: Any) -> None:
        """Route the base class's stderr access log into the module logger."""
        logger.debug(format, *args)

    def _send_health(self) -> None:
        body = b"ok\n"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_topics(self, query: str) -> list[str]:
        values = urllib.parse.parse_qs(query).get(TOPICS_PARAMETER, [])

        return [topic for value in values for topic in value.split(",") if topic]

    def _stream_events(self, topics: list[str]) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        subscriber = self.server.hub.subscribe(topics)
        try:
            self._pump_messages(subscriber)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            logger.info("subscriber %s disconnected", self.client_address)
        finally:
            self.server.hub.unsubscribe(subscriber)

    def _pump_messages(self, subscriber: queue.Queue[str]) -> None:
        while True:
            try:
                message = subscriber.get(timeout=KEEP_ALIVE_SECONDS)
                self.wfile.write(f"data: {message}\n\n".encode())
            except queue.Empty:
                self.wfile.write(b": keep-alive\n\n")

            self.wfile.flush()

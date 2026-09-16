"""The tiny webhook-to-SSE bridge that wakes the controller without polling."""

from __future__ import annotations

import argparse
import logging
import os
from http.server import ThreadingHTTPServer

from virgo_agentic_dag.server.pr_topic_extractor import PrTopicExtractor
from virgo_agentic_dag.server.sse_hub import SseHub
from virgo_agentic_dag.server.webhook_signature_verifier import WebhookSignatureVerifier
from virgo_agentic_dag.server.webhook_sse_handler import WebhookSseHandler

logger = logging.getLogger(__name__)


class WebhookSseServer(ThreadingHTTPServer):
    """Serves /webhook for GitHub deliveries and /events for SSE subscribers."""

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        hub: SseHub,
        verifier: WebhookSignatureVerifier,
        extractor: PrTopicExtractor,
    ) -> None:
        super().__init__(address, WebhookSseHandler)
        self.hub = hub
        self.verifier = verifier
        self.extractor = extractor


def main() -> int:
    """Run the bridge until interrupted."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    parser = argparse.ArgumentParser(
        prog="dag-webhook-sse",
        description="Bridge GitHub webhooks to server-sent events for tick listeners.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    arguments = parser.parse_args()

    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET is not set")

        return 2

    hub = SseHub()
    verifier = WebhookSignatureVerifier(secret)
    extractor = PrTopicExtractor()
    server = WebhookSseServer(
        (arguments.host, arguments.port), hub, verifier, extractor
    )
    logger.info("listening on http://%s:%d", arguments.host, arguments.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
    finally:
        server.server_close()

    return 0

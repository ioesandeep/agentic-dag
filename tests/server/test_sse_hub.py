import pytest
from virgo_agentic_dag.server.sse_hub import SseHub

pytestmark = pytest.mark.unit

TOPIC = "acme/virgo#12"


def test_publish_reaches_every_subscriber_of_its_topic() -> None:
    hub = SseHub()
    first = hub.subscribe([TOPIC])
    second = hub.subscribe([TOPIC])

    hub.publish("poke", [TOPIC])

    assert first.get(timeout=1) == "poke"
    assert second.get(timeout=1) == "poke"


def test_unsubscribed_queue_receives_nothing() -> None:
    hub = SseHub()
    subscriber = hub.subscribe([TOPIC])
    hub.unsubscribe(subscriber)

    hub.publish("poke", [TOPIC])

    assert subscriber.empty()


def test_count_subscribers_tracks_registration() -> None:
    hub = SseHub()
    subscriber = hub.subscribe([TOPIC])

    assert hub.count_subscribers() == 1

    hub.unsubscribe(subscriber)

    assert hub.count_subscribers() == 0


def test_delivers_only_to_the_subscribers_of_a_published_topic() -> None:
    hub = SseHub()
    watching = hub.subscribe([TOPIC])
    elsewhere = hub.subscribe(["acme/virgo#99"])

    hub.publish("pull_request", [TOPIC])

    assert watching.get(timeout=1) == "pull_request"
    assert elsewhere.empty()


def test_an_empty_subscription_hears_nothing() -> None:
    hub = SseHub()
    silent = hub.subscribe([])

    hub.publish("pull_request", [TOPIC])
    hub.publish("push", [])

    assert silent.empty()


def test_topic_subscribers_never_see_a_message_without_topics() -> None:
    hub = SseHub()
    watching = hub.subscribe([TOPIC])

    hub.publish("push", [])

    assert watching.empty()

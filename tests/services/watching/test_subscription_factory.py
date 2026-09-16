import pytest
from virgo_agentic_dag.services.watching.subscription_factory import SubscriptionFactory

pytestmark = pytest.mark.unit


def test_scopes_the_stream_address_to_the_topics() -> None:
    url = SubscriptionFactory().get_url(
        "http://stream:8787/events", ["acme/virgo#12", "acme/virgo#15"]
    )

    assert url == "http://stream:8787/events?topics=acme/virgo%2312,acme/virgo%2315"


def test_appends_to_a_query_the_address_already_carries() -> None:
    url = SubscriptionFactory().get_url("http://stream/events?keep=1", ["acme/virgo#3"])

    assert url == "http://stream/events?keep=1&topics=acme/virgo%233"

import threading
import time
from collections.abc import Iterator
from itertools import chain, repeat

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.platform.stream_error import StreamError
from virgo_agentic_dag.domain.infra.streaming.event_stream import EventStream
from virgo_agentic_dag.services.watching.event_reader import EventReader

pytestmark = pytest.mark.unit


def wait_for_thread_end(reader: EventReader) -> None:
    deadline = time.monotonic() + 5
    while reader.is_running():
        if time.monotonic() > deadline:
            raise AssertionError("reader thread never ended")

        time.sleep(0.01)


def test_get_event_delivers_payloads_across_reconnects(mocker: MockerFixture) -> None:
    stream = mocker.MagicMock(spec=EventStream)
    stream.subscribe.side_effect = chain(
        [iter(["one"]), StreamError("connection lost"), iter(["two"])],
        repeat(StreamError("connection lost")),
    )
    reader = EventReader(stream, reconnect_seconds=0.01)

    reader.start()

    assert reader.get_event(timeout_seconds=2) == "one"
    assert reader.get_event(timeout_seconds=2) == "two"
    reader.stop()


def test_get_event_returns_none_when_the_wait_runs_out(mocker: MockerFixture) -> None:
    stream = mocker.MagicMock(spec=EventStream)
    stream.subscribe.side_effect = StreamError("nothing left")
    reader = EventReader(stream, reconnect_seconds=0.01)

    reader.start()

    assert reader.get_event(timeout_seconds=0.05) is None
    reader.stop()


def test_stop_ends_the_reader_thread_when_a_read_is_parked(
    mocker: MockerFixture,
) -> None:
    is_reading = threading.Event()
    is_closed = threading.Event()

    def park() -> Iterator[str]:
        """Stand in for a read that no timeout breaks, ending only on close."""
        is_reading.set()
        is_closed.wait()

        raise StreamError("connection closed")

    stream = mocker.MagicMock(spec=EventStream)
    stream.subscribe.side_effect = park
    stream.close.side_effect = is_closed.set
    reader = EventReader(stream, reconnect_seconds=0.01)

    reader.start()

    assert is_reading.wait(timeout=5)
    reader.stop()
    wait_for_thread_end(reader)

    assert not reader.is_running()

import sys

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.host.sleep_inhibitor import SleepInhibitor
from virgo_agentic_dag.domain.infra.scheduling.host_platform import HostPlatform
from virgo_agentic_dag.infra.host.caffeinate_sleep_inhibitor import (
    CaffeinateSleepInhibitor,
)
from virgo_agentic_dag.infra.host.sleep_inhibitor_factory import SleepInhibitorFactory
from virgo_agentic_dag.infra.host.systemd_sleep_inhibitor import SystemdSleepInhibitor

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("host_platform", "sleep_inhibitor_type"),
    [
        (HostPlatform.MAC, CaffeinateSleepInhibitor),
        (HostPlatform.LINUX, SystemdSleepInhibitor),
    ],
)
def test_returns_the_sleep_inhibitor_for_the_operating_system_of_the_host(
    mocker: MockerFixture,
    host_platform: HostPlatform,
    sleep_inhibitor_type: type[SleepInhibitor],
) -> None:
    mocker.patch.object(sys, "platform", host_platform.value)
    sleep_inhibitor_factory = SleepInhibitorFactory()

    sleep_inhibitor = sleep_inhibitor_factory.get_sleep_inhibitor()

    assert isinstance(sleep_inhibitor, sleep_inhibitor_type)


def test_raises_a_config_error_when_the_host_is_windows(mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "platform", HostPlatform.WINDOWS.value)
    sleep_inhibitor_factory = SleepInhibitorFactory()

    with pytest.raises(ConfigError, match="no sleep inhibitor is known for win32"):
        sleep_inhibitor_factory.get_sleep_inhibitor()

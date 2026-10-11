import sys

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.scheduling.host_platform import HostPlatform
from virgo_agentic_dag.infra.scheduling.launchd_scheduler import LaunchdScheduler
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.infra.scheduling.systemd_scheduler import SystemdScheduler

pytestmark = pytest.mark.unit


def stand_on(monkeypatch: pytest.MonkeyPatch, host_platform: HostPlatform) -> None:
    monkeypatch.setattr(sys, "platform", host_platform.value)


def test_returns_the_launchd_scheduler_when_the_host_is_a_mac(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    stand_on(monkeypatch, HostPlatform.MAC)
    factory = SchedulerFactory(command_runner=mocker.MagicMock(spec=CommandRunner))

    scheduler = factory.get_scheduler()

    assert isinstance(scheduler, LaunchdScheduler)


def test_returns_the_systemd_scheduler_when_the_host_is_linux(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(sys, "platform", HostPlatform.LINUX.value)
    factory = SchedulerFactory(command_runner=mocker.MagicMock(spec=CommandRunner))

    scheduler = factory.get_scheduler()

    assert isinstance(scheduler, SystemdScheduler)


def test_says_no_job_system_is_known_when_the_host_has_none(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    stand_on(monkeypatch, HostPlatform.WINDOWS)
    factory = SchedulerFactory(command_runner=mocker.MagicMock(spec=CommandRunner))

    with pytest.raises(ConfigError, match="no job system is known for win32"):
        factory.get_scheduler()


def test_says_the_host_is_unknown_when_it_is_not_one_we_name(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(sys, "platform", "freebsd14")
    factory = SchedulerFactory(command_runner=mocker.MagicMock(spec=CommandRunner))

    with pytest.raises(ConfigError, match="freebsd14 is not a platform"):
        factory.get_scheduler()

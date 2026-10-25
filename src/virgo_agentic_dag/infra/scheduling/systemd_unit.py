from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.labels.en import LABELS


@dataclass(frozen=True)
class SystemdUnit:
    """Defines a scheduled unit file or its removal."""

    path: Path
    content: bytes | None

    @classmethod
    def list_for_job(cls, job: ScheduledJob) -> list[SystemdUnit]:
        """Creates the service and timer definitions for a scheduled job."""
        unit_directory = cls._get_directory(job)
        unit_name = cls.get_name(job)
        service = cls._get_service(job)
        service_content = service.encode()

        timer = cls._render_template(
            "scheduled_job.timer.j2", interval_seconds=job.interval_seconds
        )

        timer_content = timer.encode()

        return [
            cls(unit_directory / (unit_name + ".service"), service_content),
            cls(unit_directory / (unit_name + ".timer"), timer_content),
        ]

    @staticmethod
    def _get_directory(job: ScheduledJob) -> Path:
        environment = job.get_environment()
        home = environment.get("HOME")
        if home is None:
            home_path = Path.home()
            home = str(home_path)

        current_config_home = os.getenv("XDG_CONFIG_HOME", "")
        config_home = environment.get("XDG_CONFIG_HOME", current_config_home)

        config_path = Path(config_home)
        is_absolute = config_path.is_absolute()
        if not is_absolute:
            config_path = Path(home) / ".config"

        return config_path / "systemd" / "user"

    @staticmethod
    def get_name(job: ScheduledJob) -> str:
        """Returns the systemd identifier for a scheduled job."""
        characters: list[str] = []
        label_bytes = job.label.encode()
        for byte in label_bytes:
            character = chr(byte)
            if character == "/":
                characters.append("-")
            elif (
                character
                in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_."
            ):
                characters.append(character)
            else:
                characters.append(f"\\x{byte:02x}")

        unit_name = "".join(characters)
        starts_with_dot = unit_name.startswith(".")
        if starts_with_dot:
            unit_name = "\\x2e" + unit_name[1:]

        return unit_name

    @classmethod
    def _get_service(cls, job: ScheduledJob) -> str:
        argv = job.get_argv()
        arguments = [cls._quote(argument) for argument in argv]
        command = " ".join(arguments)

        working_directory = cls._get_path_value(job.working_directory)
        log_path = cls._get_path_value(job.log_path)

        environment = job.get_environment()
        assignments = [
            cls._quote(f"{key}={value}") for key, value in environment.items()
        ]

        environment_text = " ".join(assignments)

        return cls._render_template(
            "scheduled_job.service.j2",
            command=command,
            working_directory=working_directory,
            environment=environment_text,
            log_path=log_path,
        )

    @staticmethod
    def _render_template(template_name: str, **values: str | int) -> str:
        try:
            loader = PackageLoader("virgo_agentic_dag", "infra/scheduling/templates")
            environment = Environment(
                loader=loader,
                autoescape=False,
                undefined=StrictUndefined,
                keep_trailing_newline=True,
            )

            template = environment.get_template(template_name)

            return template.render(values)
        except (OSError, TemplateError, ValueError) as error:
            message = LABELS["systemdTemplateFailed"].format(
                template=template_name, error=error
            )

            raise SchedulingError(message) from error

    @staticmethod
    def _quote(value: str) -> str:
        escaped_value = value.replace("%", "%%")

        return json.dumps(escaped_value, ensure_ascii=False)

    @staticmethod
    def _get_path_value(value: str) -> str:
        ends_with_backslash = value.endswith("\\")
        if "\n" in value or "\r" in value or "\0" in value or ends_with_backslash:
            raise SchedulingError(LABELS["systemdPathInvalid"])

        return value.replace("%", "%%")

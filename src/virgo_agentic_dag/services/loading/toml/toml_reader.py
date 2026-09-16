"""Reads and validates typed values out of a parsed TOML table."""

from __future__ import annotations


class TomlReader:
    """Pulls validated strings, lists, and integers from a TOML table, raising a given error."""

    def __init__(self, error: type[Exception]) -> None:
        self._error = error

    def require_table(self, value: object, where: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise self._error(f"{where}: expected a table")

        return value

    def require_str(self, table: dict[str, object], key: str, where: str) -> str:
        value = table.get(key)
        if not isinstance(value, str) or not value:
            raise self._error(f"{where}: missing or non-string {key!r}")

        return value

    def get_str_tuple(
        self, table: dict[str, object], key: str, where: str
    ) -> tuple[str, ...]:
        value = table.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise self._error(f"{where}: {key!r} must be a list of strings")

        return tuple(value)

    def get_list(self, table: dict[str, object], key: str, where: str) -> list[object]:
        value = table.get(key, [])
        if not isinstance(value, list):
            raise self._error(f"{where}: {key!r} must be a list")

        return value

    def get_positive_int(
        self, table: dict[str, object], key: str, default: int, where: str
    ) -> int:
        value = table.get(key, default)
        if not isinstance(value, int) or value < 1:
            raise self._error(f"{where}: {key!r} must be a positive integer")

        return value

import pytest
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.services.loading.toml.toml_reader import TomlReader

pytestmark = pytest.mark.unit


def test_require_str_returns_the_value():
    assert TomlReader(ConfigError).require_str({"k": "v"}, "k", "w") == "v"


def test_require_str_rejects_missing():
    with pytest.raises(ConfigError):
        TomlReader(ConfigError).require_str({}, "k", "w")


def test_read_str_tuple_defaults_to_empty():
    assert TomlReader(ConfigError).get_str_tuple({}, "k", "w") == ()


def test_read_str_tuple_rejects_non_strings():
    with pytest.raises(ConfigError):
        TomlReader(ConfigError).get_str_tuple({"k": [1]}, "k", "w")


def test_read_positive_int_uses_default():
    assert TomlReader(ConfigError).get_positive_int({}, "k", 2, "w") == 2


def test_read_positive_int_rejects_zero():
    with pytest.raises(ConfigError):
        TomlReader(ConfigError).get_positive_int({"k": 0}, "k", 2, "w")


def test_raises_the_injected_error_type():
    with pytest.raises(ValueError):
        TomlReader(ValueError).require_str({}, "k", "w")

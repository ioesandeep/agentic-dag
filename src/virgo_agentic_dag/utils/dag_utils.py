from pathlib import Path


def get_default_db_file_name() -> str:
    return "db.sqlite3"


def get_graph_file_name() -> str:
    return "dag.toml"


def get_learnings_file_name() -> str:
    return "memory.md"


def get_dag_root() -> Path:
    return Path.home() / ".virgo-dag"


def get_dag_home(dag_name: str) -> Path:
    """Return the directory this dag's database and graph live in."""
    return get_dag_root() / dag_name


def get_dag_db_path(dag_name: str) -> Path:
    return get_dag_home(dag_name) / get_default_db_file_name()


def get_dag_graph_path(dag_name: str) -> Path:
    return get_dag_home(dag_name) / get_graph_file_name()


def get_learnings_file_path(dag_name: str) -> Path:
    return get_dag_home(dag_name) / get_learnings_file_name()


def get_dag_watch_log_path(dag_name: str) -> Path:
    return get_dag_home(dag_name) / "watch.log"


def get_runbook_text(module_file: Path, runbook_file_name: str) -> str:
    """Loads runbook text for a module."""
    return (module_file.parent / runbook_file_name).read_text(encoding="utf-8")

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_TOOL = Path(__file__).resolve().parents[2] / "tools" / "block_padding.py"


def _run(source: str, tmp_path: Path) -> tuple[int, str]:
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(_TOOL), str(sample)],
        capture_output=True,
        text=True,
    )

    return result.returncode, result.stdout


def test_flags_missing_blank_after_block(tmp_path: Path) -> None:
    code, out = _run("def f():\n    if a:\n        b()\n    c()\n", tmp_path)
    assert code == 1
    assert "after the preceding if block" in out


def test_accepts_blank_after_block(tmp_path: Path) -> None:
    code, out = _run("def f():\n    if a:\n        b()\n\n    c()\n", tmp_path)
    assert code == 0
    assert out == ""


def test_flags_missing_blank_before_return(tmp_path: Path) -> None:
    code, out = _run("def f():\n    x = 1\n    return x\n", tmp_path)
    assert code == 1
    assert "before this return" in out


def test_accepts_blank_before_return(tmp_path: Path) -> None:
    code, _ = _run("def f():\n    x = 1\n\n    return x\n", tmp_path)
    assert code == 0


def test_guard_clause_return_needs_no_blank(tmp_path: Path) -> None:
    code, _ = _run("def f():\n    if a:\n        return 1\n\n    return 2\n", tmp_path)
    assert code == 0


def test_docstring_before_return_needs_no_blank(tmp_path: Path) -> None:
    code, _ = _run('def f():\n    """Doc."""\n    return 1\n', tmp_path)
    assert code == 0

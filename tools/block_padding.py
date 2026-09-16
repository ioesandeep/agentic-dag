"""Enforce the vertical block-padding rules ruff and black cannot (CODING_RULEBOOK.md
'Vertical spacing'): the Python analogue of eslint's padding-line-between-statements.

Run as `python packages/virgo-agentic-dag/tools/block_padding.py <path> ...`; exits
non-zero and prints one `path:line: message` per missing blank line.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from pathlib import Path

_COMPOUND: tuple[type[ast.stmt], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)
if hasattr(ast, "Match"):
    _COMPOUND = (*_COMPOUND, ast.Match)

_TERMINAL: tuple[type[ast.stmt], ...] = (ast.Return, ast.Raise)


def check_source(source: str, path: str) -> list[str]:
    """Return one message per missing blank line; an empty list means the source is padded."""
    problems: list[str] = []
    tree = ast.parse(source)

    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                _check_block(block, path, problems)

    problems.sort()
    return problems


def _check_block(block: Sequence[ast.stmt], path: str, problems: list[str]) -> None:
    for prev, curr in zip(block, block[1:]):
        if prev is block[0] and _is_docstring(prev):
            continue

        end = prev.end_lineno
        if end is None or _get_start_line(curr) - end >= 2:
            continue

        if isinstance(prev, _COMPOUND):
            problems.append(
                f"{path}:{_get_start_line(curr)}: add a blank line after the preceding "
                f"{_get_node_name(prev)} block"
            )
        elif isinstance(curr, _TERMINAL):
            problems.append(
                f"{path}:{_get_start_line(curr)}: add a blank line before this {_get_node_name(curr)}"
            )


def _get_start_line(node: ast.stmt) -> int:
    decorators = getattr(node, "decorator_list", None)
    if (
        isinstance(decorators, list)
        and decorators
        and isinstance(decorators[0], ast.expr)
    ):
        return decorators[0].lineno

    return node.lineno


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _get_node_name(node: ast.stmt) -> str:
    return type(node).__name__.removesuffix("Def").lower()


def check_paths(paths: Sequence[Path]) -> list[str]:
    """Check every given file, or every ``*.py`` under a given directory."""
    problems: list[str] = []
    for path in paths:
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for file in files:
            problems += check_source(file.read_text(encoding="utf-8"), str(file))

    return problems


def main(argv: Sequence[str]) -> int:
    problems = check_paths([Path(arg) for arg in argv])
    for problem in problems:
        print(problem)

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

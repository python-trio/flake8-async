"""Additional tests for command line parameters and decorator handling."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from flake8_async import main
from flake8_async.base import Statement
from flake8_async.visitors.helpers import fnmatch_qualified_name
from flake8_async.visitors.visitor91x import Visitor91X

if TYPE_CHECKING:
    import pytest


def dec_list(*decorators: str) -> ast.Module:
    source = ""
    for dec in decorators:
        source += f"@{dec}\n"
    source += "async def f():\n  bar()"
    return ast.parse(source)


def wrap(decorators: tuple[str, ...], decs2: str) -> str | None:
    tree = dec_list(*decorators)
    assert isinstance(tree.body[0], ast.AsyncFunctionDef)
    return fnmatch_qualified_name(tree.body[0].decorator_list, decs2)


def test_basic():
    assert wrap(("foo",), "foo")
    assert wrap(("foo", "bar"), "foo")
    assert wrap(("bar", "foo"), "foo")

    assert not wrap(("foo",), "foob")


def test_dotted():
    assert wrap(("foo.bar",), "foo.bar")

    assert not wrap(("foo.bar",), "foo")
    assert not wrap(("foo.bar",), "bar")

    assert not wrap(("foo",), "foo.bar")
    assert not wrap(("bar",), "foo.bar")

    assert not wrap(("foo.bar.jane",), "foo.bar")
    assert not wrap(("foo.bar",), "foo.bar.jane")
    assert not wrap(("jane.foo.bar",), "foo.bar")
    assert not wrap(("foo.bar",), "jane.foo.bar")


def test_multidotted():
    assert wrap(("foo.bar.jane",), "foo.bar.jane")
    assert not wrap(("foo.bar",), "foo.bar.jane")
    assert not wrap(("foo.bar.jane",), "foo.bar")


def test_wildcard():
    assert wrap(("foo",), "*")
    assert wrap(("foo.bar",), "*")
    assert not wrap(("foo",), "foo.*")
    assert wrap(("foo.bar",), "foo.*")
    assert not wrap(("bar.foo",), "foo.*")

    assert wrap(("foo",), "foo*")
    assert wrap(("foobar",), "foo*")
    assert wrap(("foobar.bar",), "foo*")
    assert wrap(("foo.bar",), "*.bar")


def test_at():
    assert wrap(("foo",), "@foo")
    assert wrap(("foo.bar",), "@foo.bar")


def test_calls():
    assert wrap(("foo()",), "@foo")
    assert wrap(("foo(1, 2, *x, **y)",), "@foo")
    assert wrap(("foo.bar()",), "@foo.bar")
    assert wrap(("foo.bar(1, 2, *x, **y)",), "@foo.bar")


def test_pep614():
    # Just don't crash and we'll be good.
    assert not wrap(("(any, expression, we, like)",), "no match here")


file_path = str(Path(__file__).parent / "trio_options.py")


def _set_flags(monkeypatch: pytest.MonkeyPatch, *flags: str):
    monkeypatch.setattr(
        sys, "argv", ["./flake8-async", "--enable=ASYNC910", file_path, *flags]
    )


def test_command_line_1(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _set_flags(monkeypatch, "--no-checkpoint-warning-decorators=app.route")
    assert main() == 0

    assert capfd.readouterr() == ("", "")


expected_lineno = -1
with open(file_path) as f:
    for lineno, line in enumerate(f, start=1):
        if line.startswith("async def"):
            expected_lineno = lineno
            break

expected_out = (
    f"{file_path}:{expected_lineno}:1: ASYNC910 "
    + Visitor91X.error_codes["ASYNC910"].format(
        "exit", Statement("function definition", expected_lineno)
    )
    + "\n"
)


def test_command_line_2(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _set_flags(monkeypatch, "--no-checkpoint-warning-decorators=app")
    assert main() == 1
    assert capfd.readouterr() == (expected_out, "")


def test_command_line_3(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _set_flags(monkeypatch)
    assert main() == 1
    assert capfd.readouterr() == (expected_out, "")

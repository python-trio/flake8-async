from __future__ import annotations

import ast

from flake8.main.application import Application
from test_flake8_trio import _default_option_manager

from flake8_trio import Plugin, Statement, Visitor107_108, fnmatch_qualified_name


def dec_list(*decorators: str) -> ast.Module:
    source = ""
    for dec in decorators:
        source += f"@{dec}\n"
    source += "async def f():\n  bar()"
    tree = ast.parse(source)
    return tree


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


def test_plugin():
    tree = dec_list("app.route")
    plugin = Plugin(tree)

    om = _default_option_manager()
    plugin.add_options(om)

    plugin.parse_options(om.parse_args(args=[]))
    assert tuple(plugin.run())

    arg = "--no-checkpoint-warning-decorators=app.route"
    plugin.parse_options(om.parse_args(args=[arg]))

    assert not tuple(plugin.run())


common_flags = ["--select=TRIO", "tests/trio_options.py"]


def test_command_line_1(capfd):
    Application().run(common_flags + ["--no-checkpoint-warning-decorators=app.route"])
    out, err = capfd.readouterr()
    assert not out and not err


expected_out = (
    "tests/trio_options.py:2:1: TRIO107: "
    + Visitor107_108.error_codes["TRIO107"].format(
        "exit", Statement("function definition", 2)
    )
    + "\n"
)


def test_command_line_2(capfd):
    Application().run(common_flags + ["--no-checkpoint-warning-decorators=app"])
    out, err = capfd.readouterr()
    assert out == expected_out and not err


def test_command_line_3(capfd):
    Application().run(common_flags)
    out, err = capfd.readouterr()
    assert out == expected_out and not err

import ast
from typing import Set

import flake8_trio


def _results(code: str) -> Set[str]:
    tree = ast.parse(code)
    plugin = flake8_trio.Plugin(tree)
    return {f"{line-1}:{col} {msg}" for line, col, msg, _ in plugin.run()}


def test_was_imported():
    assert flake8_trio


def test_empty():
    assert _results("") == set()


def test_unrelated_with():
    assert _results("with open('foo'):\n  pass") == set()


def test_context_no_checkpoint1():
    code = "import trio\nwith trio.move_on_after(10):\n  pass"
    assert _results(code) == {"1:0 " + flake8_trio.TRIO100.format("trio.move_on_after")}


def test_context_no_checkpoint2():
    code = "import trio\nwith trio.move_on_after(10):\n  await trio.sleep(1)"
    assert _results(code) == set()


def test_context_no_checkpoint3():
    code = (
        "import trio\n"
        "with trio.move_on_after(10):\n"
        "  pass\n"
        "  await trio.sleep(1)\n"
        "  print('hello')"
    )
    assert _results(code) == set()


def test_context_no_checkpoint4():
    code = (
        "import trio\n"
        "with trio.move_on_after(10):\n"
        "  pass\n"
        "  while True:\n"
        "    await trio.sleep(1)\n"
        "  print('hello')"
    )
    assert _results(code) == set()

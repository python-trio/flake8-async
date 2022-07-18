import ast
import unittest
from pathlib import Path
from typing import Any, List, Tuple, Type

from flake8_trio import TRIO100, Error, Plugin


class Flake8TrioTestCase(unittest.TestCase):
    def errors(self, *errors: Error) -> List[Tuple[int, int, str, Type[Any]]]:
        return [e.flake_yield() for e in errors]

    def test_tree(self):
        plugin = Plugin(tree=ast.parse(""))
        errors = list(plugin.run())
        self.assertEqual(errors, [])

    def test_trio100(self):
        filename = Path(__file__).absolute().parent / "trio100.py"
        plugin = Plugin(filename=str(filename))
        errors = list(plugin.run())
        expected = self.errors(
            TRIO100(3, 5, "trio.move_on_after"),
            TRIO100(25, 8, "trio.fail_after"),
        )
        self.assertEqual(errors, expected)

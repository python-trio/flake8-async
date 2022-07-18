import ast
import os
import site
import sys
import unittest
from pathlib import Path
from typing import Any, List, Tuple, Type

from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar

from flake8_trio import TRIO100, Error, Plugin, Visitor


class Flake8TrioTestCase(unittest.TestCase):
    def errors(self, *errors: Error) -> List[Tuple[int, int, str, Type[Any]]]:
        return [e.values() for e in errors]

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
            TRIO100(23, 15, "trio.fail_after"),
        )
        self.assertEqual(errors, expected)

    @unittest.skipIf(sys.version_info < (3, 9), "requires 3.9+")
    def test_trio100_py39(self):
        filename = Path(__file__).absolute().parent / "trio100_py39.py"
        plugin = Plugin(filename=str(filename))
        errors = list(plugin.run())
        expected = self.errors(
            TRIO100(7, 8, "trio.fail_after"),
            TRIO100(12, 8, "trio.fail_after"),
            TRIO100(14, 8, "trio.move_on_after"),
        )
        self.assertEqual(errors, expected)


class TestFuzz(unittest.TestCase):
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(from_grammar().map(ast.parse))
    def test_does_not_crash_on_any_valid_code(self, syntax_tree: ast.AST):
        # Given any syntatically-valid source code, the checker should
        # not crash.  This tests doesn't check that we do the *right* thing,
        # just that we don't crash on valid-if-poorly-styled code!
        Visitor().visit(syntax_tree)

    def test_does_not_crash_on_site_code(self):
        # Because the generator isn't perfect, we'll also test on all the code
        # we can easily find in our current Python environment - this includes
        # the standard library, and all installed packages.
        for base in sorted(set(site.PREFIXES)):
            for dirname, _, files in os.walk(base):
                for f in files:
                    if f.endswith(".py"):
                        self.assertFalse(
                            any(Plugin(filename=str(Path(dirname) / f)).run())
                        )

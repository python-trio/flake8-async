import ast
import os
import site
import sys
import unittest
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

from flake8_trio import TRIO100, TRIO101, Error, Plugin, Visitor, make_error


class Flake8TrioTestCase(unittest.TestCase):
    def assert_expected_errors(self, test_file: str, *expected: Error) -> None:
        filename = Path(__file__).absolute().parent / test_file
        plugin = Plugin.from_filename(str(filename))
        errors = tuple(plugin.run())
        self.assertEqual(errors, expected)

    def test_tree(self):
        plugin = Plugin(ast.parse(""))
        errors = list(plugin.run())
        self.assertEqual(errors, [])

    def test_trio100(self):
        self.assert_expected_errors(
            "trio100.py",
            make_error(TRIO100, 3, 5, "trio.move_on_after"),
            make_error(TRIO100, 23, 15, "trio.fail_after"),
        )

    @unittest.skipIf(sys.version_info < (3, 9), "requires 3.9+")
    def test_trio100_py39(self):
        self.assert_expected_errors(
            "trio100_py39.py",
            make_error(TRIO100, 7, 8, "trio.fail_after"),
            make_error(TRIO100, 12, 8, "trio.fail_after"),
            make_error(TRIO100, 14, 8, "trio.move_on_after"),
        )

    def test_trio101(self):
        self.maxDiff = None
        self.assert_expected_errors(
            "trio101.py",
            make_error(TRIO101, 10, 8),
            make_error(TRIO101, 15, 8),
            make_error(TRIO101, 27, 8),
            make_error(TRIO101, 38, 8),
        )


@pytest.mark.fuzz
class TestFuzz(unittest.TestCase):
    @settings(max_examples=1_000, suppress_health_check=[HealthCheck.too_slow])
    @given((from_grammar() | from_node()).map(ast.parse))
    def test_does_not_crash_on_any_valid_code(self, syntax_tree: ast.AST):
        # Given any syntatically-valid source code, the checker should
        # not crash.  This tests doesn't check that we do the *right* thing,
        # just that we don't crash on valid-if-poorly-styled code!
        Visitor().visit(syntax_tree)

    @staticmethod
    def _iter_python_files():
        # Because the generator isn't perfect, we'll also test on all the code
        # we can easily find in our current Python environment - this includes
        # the standard library, and all installed packages.
        for base in sorted(set(site.PREFIXES)):
            for dirname, _, files in os.walk(base):
                for f in files:
                    if f.endswith(".py"):
                        yield Path(dirname) / f

    def test_does_not_crash_on_site_code(self):
        for path in self._iter_python_files():
            try:
                Plugin.from_filename(str(path)).run()
            except Exception as err:
                raise AssertionError(f"Failed on {path}") from err

import ast
import inspect
import os
import site
import sys
import unittest
from pathlib import Path
from typing import Iterable

import pytest
import trio  # type: ignore
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

from flake8_trio import (
    TRIO100,
    TRIO101,
    TRIO102,
    TRIO103,
    TRIO104,
    TRIO105,
    TRIO106,
    TRIO107,
    TRIO108,
    Error,
    Plugin,
    make_error,
    trio_async_functions,
)


class Flake8TrioTestCase(unittest.TestCase):
    def assert_expected_errors(self, test_file: str, *expected: Error) -> None:
        def trim_messages(messages: Iterable[Error]):
            return tuple(((line, col, msg[:7]) for line, col, msg, _ in messages))

        filename = Path(__file__).absolute().parent / test_file
        plugin = Plugin.from_filename(str(filename))

        errors = tuple(plugin.run())

        # start with a check with trimmed errors that will make for smaller diff messages
        trim_errors = trim_messages(errors)
        trim_expected = trim_messages(expected)

        #
        unexpected = sorted(set(trim_errors) - set(trim_expected))
        missing = sorted(set(trim_expected) - set(trim_errors))
        self.assertEqual((unexpected, missing), ([], []), msg="(unexpected, missing)")

        unexpected = sorted(set(errors) - set(expected))
        missing = sorted(set(expected) - set(errors))
        if unexpected and missing:
            self.assertEqual(unexpected[0], missing[0])
        self.assertEqual((unexpected, missing), ([], []), msg="(unexpected, missing)")

        # full check
        self.assertTupleEqual(errors, expected)

    def test_tree(self):
        plugin = Plugin(ast.parse(""))
        errors = list(plugin.run())
        self.assertSequenceEqual(errors, [])

    def test_trio100(self):
        self.assert_expected_errors(
            "trio100.py",
            make_error(TRIO100, 3, 5, "trio.move_on_after"),
            make_error(TRIO100, 8, 15, "trio.fail_after"),
            make_error(TRIO100, 26, 9, "trio.fail_after"),
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
        self.assert_expected_errors(
            "trio101.py",
            make_error(TRIO101, 10, 8),
            make_error(TRIO101, 15, 8),
            make_error(TRIO101, 27, 8),
            make_error(TRIO101, 38, 8),
            make_error(TRIO101, 59, 8),
        )

    def test_trio102(self):
        self.assert_expected_errors(
            "trio102.py",
            make_error(TRIO102, 24, 8, 21, 4, "try/finally"),
            make_error(TRIO102, 30, 12, 26, 4, "try/finally"),
            make_error(TRIO102, 36, 12, 32, 4, "try/finally"),
            make_error(TRIO102, 62, 12, 55, 4, "try/finally"),
            make_error(TRIO102, 70, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 74, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 76, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 80, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 82, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 84, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 88, 12, 66, 4, "try/finally"),
            make_error(TRIO102, 92, 8, 66, 4, "try/finally"),
            make_error(TRIO102, 94, 8, 66, 4, "try/finally"),
            make_error(TRIO102, 101, 12, 98, 8, "try/finally"),
            make_error(TRIO102, 124, 12, 114, 4, "try/finally"),
            make_error(TRIO102, 135, 8, 134, 11, "trio.Cancelled"),
            make_error(TRIO102, 138, 8, 137, 11, "BaseException"),
            make_error(TRIO102, 141, 8, 140, 4, "bare except"),
        )

    def test_trio103_104(self):
        self.assert_expected_errors(
            "trio103_104.py",
            make_error(TRIO103, 7, 33, "trio.Cancelled"),
            make_error(TRIO103, 15, 7, "trio.Cancelled"),
            # raise different exception
            make_error(TRIO104, 20, 4),
            make_error(TRIO104, 22, 4),
            make_error(TRIO104, 25, 4),
            # if
            make_error(TRIO103, 28, 7, "BaseException"),
            make_error(TRIO103, 35, 7, "BaseException"),
            # loops
            make_error(TRIO103, 47, 7, "trio.Cancelled"),
            make_error(TRIO103, 52, 7, "trio.Cancelled"),
            # nested exceptions
            make_error(TRIO104, 67, 8),  # weird edge-case
            make_error(TRIO103, 61, 7, "BaseException"),
            make_error(TRIO104, 92, 8),
            # make_error(TRIO104, 94, 8), # weird edge-case
            # bare except
            make_error(TRIO103, 97, 0, "bare except"),
            # multi-line
            make_error(TRIO103, 111, 4, "BaseException"),
            # re-raise parent
            make_error(TRIO104, 124, 8),
            # return
            make_error(TRIO104, 134, 8),
            make_error(TRIO103, 133, 11, "BaseException"),
            make_error(TRIO104, 139, 12),
            make_error(TRIO104, 141, 12),
            make_error(TRIO104, 143, 12),
            make_error(TRIO104, 145, 12),
            make_error(TRIO103, 137, 11, "BaseException"),
            # continue/break
            make_error(TRIO104, 154, 12),
            make_error(TRIO104, 162, 12),
            # yield
            make_error(TRIO104, 184, 8),
            make_error(TRIO104, 190, 12),
            make_error(TRIO104, 192, 12),
            make_error(TRIO104, 194, 12),
            make_error(TRIO104, 196, 12),
        )

    def test_trio105(self):
        self.assert_expected_errors(
            "trio105.py",
            make_error(TRIO105, 25, 4, "aclose_forcefully"),
            make_error(TRIO105, 26, 4, "open_file"),
            make_error(TRIO105, 27, 4, "open_ssl_over_tcp_listeners"),
            make_error(TRIO105, 28, 4, "open_ssl_over_tcp_stream"),
            make_error(TRIO105, 29, 4, "open_tcp_listeners"),
            make_error(TRIO105, 30, 4, "open_tcp_stream"),
            make_error(TRIO105, 31, 4, "open_unix_socket"),
            make_error(TRIO105, 32, 4, "run_process"),
            make_error(TRIO105, 33, 4, "serve_listeners"),
            make_error(TRIO105, 34, 4, "serve_ssl_over_tcp"),
            make_error(TRIO105, 35, 4, "serve_tcp"),
            make_error(TRIO105, 36, 4, "sleep"),
            make_error(TRIO105, 37, 4, "sleep_forever"),
            make_error(TRIO105, 38, 4, "sleep_until"),
            make_error(TRIO105, 44, 15, "open_file"),
            make_error(TRIO105, 49, 8, "open_file"),
        )

        self.assertSetEqual(
            set(trio_async_functions),
            {
                o[0]
                for o in inspect.getmembers(trio)  # type: ignore
                if inspect.iscoroutinefunction(o[1])
            },
        )

    def test_trio106(self):
        self.assert_expected_errors(
            "trio106.py",
            make_error(TRIO106, 4, 0),
            make_error(TRIO106, 5, 0),
            make_error(TRIO106, 6, 0),
        )

    def test_trio107_108(self):
        self.assert_expected_errors(
            "trio107_108.py",
            make_error(TRIO107, 13, 0),
            # if
            make_error(TRIO107, 18, 0),
            make_error(TRIO107, 36, 0),
            # ifexp
            make_error(TRIO107, 46, 0),
            # loops
            make_error(TRIO107, 51, 0),
            make_error(TRIO107, 56, 0),
            make_error(TRIO107, 69, 0),
            make_error(TRIO107, 74, 0),
            # try
            make_error(TRIO107, 83, 0),
            # early return
            make_error(TRIO108, 141, 4),
            make_error(TRIO108, 146, 8),
            # nested function definition
            make_error(TRIO107, 150, 0),
            make_error(TRIO107, 160, 4),
            make_error(TRIO107, 164, 0),
            make_error(TRIO107, 171, 8),
            make_error(TRIO107, 169, 0),
            make_error(TRIO107, 175, 0),
        )


@pytest.mark.fuzz
class TestFuzz(unittest.TestCase):
    @settings(max_examples=1_000, suppress_health_check=[HealthCheck.too_slow])
    @given((from_grammar() | from_node()).map(ast.parse))
    def test_does_not_crash_on_any_valid_code(self, syntax_tree: ast.AST):
        # Given any syntatically-valid source code, the checker should
        # not crash.  This tests doesn't check that we do the *right* thing,
        # just that we don't crash on valid-if-poorly-styled code!
        Plugin(syntax_tree).run()

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

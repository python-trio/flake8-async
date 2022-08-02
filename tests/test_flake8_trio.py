import ast
import os
import re
import site
import sys
import unittest
from pathlib import Path
from typing import Iterable, List, Tuple

import pytest

# import trio  # type: ignore
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

import flake8_trio
from flake8_trio import Error, Plugin, make_error

test_files: List[Tuple[str, str]] = sorted(
    (os.path.splitext(f)[0].upper(), f)
    for f in os.listdir("tests")
    if re.match(r"^trio.*.py", f)
)


# These functions are messily cobbled together and their formatting requirements
# should be documented in the readme
#
# filename: trioXXX.py
# or: trioXXX_pyXY*.py, where X is major and Y is minor version
# triggers on lines with error: <col>[, <param>]...
# only checks the error message matching the file name
@pytest.mark.parametrize("test, path", test_files)
def test_eval(test: str, path: str):
    # version check
    python_version = re.search(r"(?<=_PY)\d*", test)
    if python_version:
        version_str = python_version.group()
        major, minor = version_str[0], version_str[1:]
        v_i = sys.version_info
        if (v_i.major, v_i.minor) < (int(major), int(minor)):
            return
        test = test.split("_")[0]

    error_msg = getattr(flake8_trio, test)
    expected: List[Error] = []
    with open(os.path.join("tests", path)) as file:
        for lineno, line in enumerate(file):
            # get text between `error: ` and newline
            k = re.search(r"(?<=error: ).*(?=\n)", line)
            if not k:
                continue
            # Append a bunch of 0's so string formatting gives garbage instead
            # of throwing an exception
            args = [m.strip() for m in k.group().split(",")] + ["0"] * 5
            col, *args = args
            expected.append(make_error(error_msg, lineno + 1, int(col), *args))

    assert_expected_errors(path, test, *expected)


# This function is also a mess now, but I keep slowly iterating on getting it to
# print actually helpful error messages in all cases - which is a struggle.
# It'll likely continue to be a mess for the foreseeable future
def assert_expected_errors(test_file: str, include: str, *expected: Error) -> None:
    def trim_messages(messages: Iterable[Error]):
        return tuple(((line, col, int(msg[4:7])) for line, col, msg, _ in messages))

    filename = Path(__file__).absolute().parent / test_file
    plugin = Plugin.from_filename(str(filename))

    errors = tuple(e for e in plugin.run() if include in e[2])

    # start with a check with trimmed errors that will make for smaller diff messages
    trim_errors = trim_messages(errors)
    trim_expected = trim_messages(expected)

    cls = unittest.TestCase()
    unexpected = sorted(set(trim_errors) - set(trim_expected))
    missing = sorted(set(trim_expected) - set(trim_errors))
    cls.assertEqual((unexpected, missing), ([], []), msg="(unexpected, missing)")

    unexpected = sorted(set(errors) - set(expected))
    missing = sorted(set(expected) - set(errors))
    if unexpected and missing:
        cls.assertEqual(unexpected[0], missing[0])
    cls.assertEqual((unexpected, missing), ([], []), msg="(unexpected, missing)")

    # full check
    cls.assertSequenceEqual(sorted(errors), sorted(expected))


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

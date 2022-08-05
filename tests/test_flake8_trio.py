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
            raise unittest.SkipTest("v_i, major, minor")
        test = test.split("_")[0]

    error_msg = getattr(flake8_trio, test)
    expected: List[Error] = []
    with open(os.path.join("tests", path)) as file:
        for lineno, line in enumerate(file, start=1):
            # get text between `error:` and end of line
            k = re.search(r"(?<=error:).*$", line)
            if not k or line.strip()[0] == "#":
                continue
            # Append a bunch of empty strings so string formatting gives garbage instead
            # of throwing an exception
            args = [m.strip() for m in k.group().split(",")] + [""] * 5
            col, *args = args
            for i, arg in enumerate(args):
                if "$lineno" in arg:
                    args[i] = eval(arg.replace("$", ""), {"lineno": lineno})
            assert col.isdigit(), f'invalid column "{col}" @L{lineno}, in "{line}"'
            expected.append(make_error(error_msg, lineno, int(col), *args))

    assert expected, "failed to parse any errors in file"
    assert_expected_errors(path, test, *expected)


def assert_expected_errors(test_file: str, include: str, *expected: Error):
    filename = Path(__file__).absolute().parent / test_file
    plugin = Plugin.from_filename(str(filename))

    errors = tuple(sorted(e for e in plugin.run() if include in e[2]))
    expected = tuple(sorted(expected))

    assert_correct_lines(errors, expected)
    assert_correct_columns(errors, expected)
    assert_correct_messages(errors, expected)

    # full check
    unittest.TestCase().assertSequenceEqual(sorted(errors), sorted(expected))


def assert_correct_lines(errors: Iterable[Error], expected: Iterable[Error]):
    # Check that errors are on correct lines
    error_lines = {line for line, *_ in errors}
    expected_lines = {line for line, *_ in expected}
    unexpected_lines = sorted(error_lines - expected_lines)
    missing_lines = sorted(expected_lines - error_lines)
    unittest.TestCase().assertEqual(
        unexpected_lines,
        missing_lines,
        msg="Lines with unexpected errors; missing errors",
    )


def assert_correct_columns(errors: Iterable[Error], expected: Iterable[Error]):
    # check errors have correct columns
    col_error = False
    for (line, error_col, *_), (_, expected_col, *_) in zip(errors, expected):
        if error_col != expected_col:
            if not col_error:
                print("Errors with same line but different columns:", file=sys.stderr)
                print("| line | actual | expected |", file=sys.stderr)
                col_error = True
            print(
                f"| {line:4} | {error_col:6} | {expected_col:8} |",
                file=sys.stderr,
            )
    assert not col_error


def assert_correct_messages(errors: Iterable[Error], expected: Iterable[Error]):
    # check errors have correct messages
    msg_error = False
    for (line, _, error_msg, *_), (_, _, expected_msg, *_) in zip(errors, expected):
        if error_msg != expected_msg:
            if not msg_error:
                print(
                    "Errors with different messages:",
                    "-" * 20,
                    sep="\n",
                    file=sys.stderr,
                )
                msg_error = True
            print(
                f"*   line: {line:3}",
                f"  actual: {error_msg}",
                f"expected: {expected_msg}",
                "-" * 20,
                sep="\n",
                file=sys.stderr,
            )
    assert not msg_error


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

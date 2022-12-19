from __future__ import annotations

import ast
import copy
import itertools
import os
import re
import site
import subprocess
import sys
import tokenize
import unittest
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import DefaultDict

import pytest
from flake8 import __version_info__ as flake8_version_info
from flake8.options.manager import OptionManager

# import trio  # type: ignore
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

from flake8_trio import Error, Flake8TrioVisitor, Plugin, Statement

trio_test_files_regex = re.compile(r"trio\d\d\d(_py.*)?.py")

test_files: list[tuple[str, str]] = sorted(
    (os.path.splitext(f)[0].upper(), f)
    for f in os.listdir("tests")
    if re.match(trio_test_files_regex, f)
)


class ParseError(Exception):
    ...


# flake8 6 added a required named parameter formatter_names
def _default_option_manager():
    kwargs = {}
    if flake8_version_info[0] >= 6:
        kwargs["formatter_names"] = ["default"]
    return OptionManager(version="", plugin_versions="", parents=[], **kwargs)


# check for presence of _pyXX, skip if version is later, and prune parameter
def check_version(test: str) -> str:
    python_version = re.search(r"(?<=_PY)\d*", test)
    if python_version:
        version_str = python_version.group()
        major, minor = version_str[0], version_str[1:]
        v_i = sys.version_info
        if (v_i.major, v_i.minor) < (int(major), int(minor)):
            raise unittest.SkipTest("v_i, major, minor")
        return test.split("_")[0]
    return test


ERROR_CODES = {
    err_code: err_class
    for err_class in Flake8TrioVisitor.__subclasses__()
    for err_code in err_class.error_codes.keys()
}


@pytest.mark.parametrize("test, path", test_files)
def test_eval(test: str, path: str):
    # version check
    test = check_version(test)

    assert test in ERROR_CODES, "error code not defined in flake8_trio.py"

    include = [test]
    parsed_args = [""]
    expected: list[Error] = []

    with open(os.path.join("tests", path), encoding="utf-8") as file:
        lines = file.readlines()

    for lineno, line in enumerate(lines, start=1):
        line = line.strip()

        # add other error codes to check if #INCLUDE is specified
        if reg_match := re.search(r"(?<=INCLUDE).*", line):
            for other_code in reg_match.group().split(" "):
                if other_code.strip():
                    include.append(other_code.strip())

        # add command-line args if specified with #ARGS
        elif reg_match := re.search(r"(?<=ARGS).*", line):
            for arg in reg_match.group().split(" "):
                if arg.strip():
                    parsed_args.append(arg.strip())

        # skip commented out lines
        if not line or line[0] == "#":
            continue

        # get text between `error:` and (end of line or another comment)
        k = re.findall(r"(error|TRIO...):([^#]*)(?=#|$)", line)

        for err_code, err_args in k:
            try:
                # Append a bunch of empty strings so string formatting gives garbage
                # instead of throwing an exception
                try:
                    args = eval(
                        f"[{err_args}]",
                        {
                            "lineno": lineno,
                            "line": lineno,
                            "Statement": Statement,
                            "Stmt": Statement,
                        },
                    )
                except NameError:
                    print(f"failed to eval on line {lineno}", file=sys.stderr)
                    raise

            except Exception as e:
                print(f"lineno: {lineno}, line: {line}", file=sys.stderr)
                raise e

            if args:
                col, *args = args
            else:
                col = 0
            assert isinstance(
                col, int
            ), f'invalid column "{col}" @L{lineno}, in "{line}"'

            if err_code == "error":
                err_code = test
            error_class = ERROR_CODES[err_code]
            message = error_class.error_codes[err_code]
            try:
                expected.append(Error(err_code, lineno, int(col), message, *args))
            except AttributeError as e:
                msg = (
                    f"Line {lineno}: Failed to format\n {message!r}\n" f'"with\n{args}'
                )
                raise ParseError(msg) from e

    assert expected, f"failed to parse any errors in file {path}"

    plugin = read_file(path)
    assert_expected_errors(plugin, include, *expected, args=parsed_args)


# Codes that are supposed to also raise errors when run on sync code, and should
# be excluded from the SyncTransformer check.
# Expand this list when adding a new check if it does not care about whether the code
# is asynchronous or not.
error_codes_ignored_when_checking_transformed_sync_code = {
    "TRIO100",
    "TRIO101",
    "TRIO103",
    "TRIO104",
    "TRIO105",
    "TRIO106",
    "TRIO111",
    "TRIO112",
    "TRIO115",
    "TRIO116",
}


class SyncTransformer(ast.NodeTransformer):
    def visit_Await(self, node: ast.Await):
        newnode = self.generic_visit(node.value)
        return newnode

    def replace_async(self, node: ast.AST, target: type[ast.AST]) -> ast.AST:
        node = self.generic_visit(node)
        newnode = target()
        newnode.__dict__ = node.__dict__
        return newnode

    def visit_AsyncFunctionDef(self, node: ast.AST):
        return self.replace_async(node, ast.FunctionDef)

    def visit_AsyncWith(self, node: ast.AST):
        return self.replace_async(node, ast.With)

    def visit_AsyncFor(self, node: ast.AST):
        return self.replace_async(node, ast.For)


@pytest.mark.parametrize("test, path", test_files)
def test_noerror_on_sync_code(test: str, path: str):
    if any(e in test for e in error_codes_ignored_when_checking_transformed_sync_code):
        return
    with tokenize.open(f"tests/{path}") as f:
        source = f.read()
    tree = SyncTransformer().visit(ast.parse(source))

    assert_expected_errors(
        Plugin(tree),
        include=error_codes_ignored_when_checking_transformed_sync_code,
        invert_include=True,
    )


def read_file(test_file: str):
    filename = Path(__file__).absolute().parent / test_file
    return Plugin.from_filename(str(filename))


def assert_expected_errors(
    plugin: Plugin,
    include: Iterable[str],
    *expected: Error,
    args: list[str] | None = None,
    invert_include: bool = False,
):
    # initialize default option values
    om = _default_option_manager()
    plugin.add_options(om)
    plugin.parse_options(om.parse_args(args=(args if args else [""])))

    errors = sorted(
        e
        for e in plugin.run()
        if (e.code in include if not invert_include else e.code not in include)
    )
    expected_ = sorted(expected)

    print_first_diff(errors, expected_)
    assert_correct_lines_and_codes(errors, expected_)
    assert_correct_columns(errors, expected_)
    assert_correct_args(errors, expected_)

    # full check
    unittest.TestCase().assertEqual(errors, expected_)

    # test tuple conversion and iter types
    assert_tuple_and_types(errors, expected_)


def print_first_diff(errors: Sequence[Error], expected: Sequence[Error]):
    first_error_line: list[Error] = []
    first_expected_line: list[Error] = []
    for err, exp in zip(errors, expected):
        if err == exp:
            continue
        if not first_error_line or err.line == first_error_line[0]:
            first_error_line.append(err)
        if not first_expected_line or exp.line == first_expected_line[0]:
            first_expected_line.append(exp)

    if first_expected_line != first_error_line:
        print(
            "First lines with different errors",
            f"  actual: {[e.cmp() for e in first_error_line]}",
            f"expected: {[e.cmp() for e in first_expected_line]}",
            "",
            sep="\n",
            file=sys.stderr,
        )


def assert_correct_lines_and_codes(errors: Iterable[Error], expected: Iterable[Error]):
    MyDict = DefaultDict[int, DefaultDict[str, int]]
    # Check that errors are on correct lines
    all_lines = sorted({e.line for e in (*errors, *expected)})
    error_dict: MyDict = DefaultDict(lambda: DefaultDict(int))
    expected_dict = copy.deepcopy(error_dict)

    for e in errors:
        error_dict[e.line][e.code] += 1
    for e in expected:
        expected_dict[e.line][e.code] += 1

    any_error = False
    for line in all_lines:
        if error_dict[line] == expected_dict[line]:
            continue
        for code in sorted({*error_dict[line], *expected_dict[line]}):
            if not any_error:
                print(
                    "Lines with different # of errors:",
                    "-" * 38,
                    f"| line | {'code':7} | actual | expected |",
                    sep="\n",
                    file=sys.stderr,
                )
                any_error = True

            print(
                f"| {line:4}",
                f"{code}",
                f"{error_dict[line][code]:6}",
                f"{expected_dict[line][code]:8} |",
                sep=" | ",
                file=sys.stderr,
            )
    assert not any_error


def assert_correct_columns(errors: Iterable[Error], expected: Iterable[Error]):
    # check errors have correct columns
    col_error = False
    for err, exp in zip(errors, expected):
        assert err.line == exp.line
        if err.col != exp.col:
            if not col_error:
                print("Errors with same line but different columns:", file=sys.stderr)
                print("| line | actual | expected |", file=sys.stderr)
                col_error = True
            print(
                f"| {err.line:4} | {err.col:6} | {exp.col:8} |",
                file=sys.stderr,
            )
    assert not col_error


def assert_correct_args(errors: Iterable[Error], expected: Iterable[Error]):
    # check errors have correct messages
    args_error = False
    for err, exp in zip(errors, expected):
        assert (err.line, err.col, err.code) == (exp.line, exp.col, exp.code)
        if err.args != exp.args:
            if not args_error:
                print(
                    "Errors with different args:",
                    "-" * 20,
                    sep="\n",
                    file=sys.stderr,
                )
                args_error = True
            print(
                f"*    line: {err.line:3} differs\n",
                f"  actual: {err.args}\n",
                f"expected: {exp.args}\n",
                "-" * 20,
                file=sys.stderr,
            )
    assert not args_error


def assert_tuple_and_types(errors: Iterable[Error], expected: Iterable[Error]):
    def info_tuple(error: Error):
        try:
            return tuple(error)
        except IndexError:
            print(
                "Failed to format error message",
                f"line: {error.line}",
                f"col: {error.col}",
                f"code: {error.code}",
                f"args: {error.args}",
                f'format string: "{ERROR_CODES[error.code].error_codes[error.code]}"',
                sep="\n    ",
                file=sys.stderr,
            )
            raise

    for err, exp in zip(errors, expected):
        err_msg = info_tuple(err)
        for err, type_ in zip(err_msg, (int, int, str, type)):
            assert isinstance(err, type_)
        assert err_msg == info_tuple(exp)


def test_107_permutations():
    # since each test is so fast, and there's so many permutations, manually doing
    # the permutations in a single test is much faster than the permutations from using
    # pytest parametrization - and does not clutter up the output massively.
    check = "await foo()"
    for try_, exc1, exc2, bare_exc, else_, finally_ in itertools.product(
        (check, "..."),
        (check, "...", "raise", "return", None),
        (check, "...", "raise", "return", None),
        (check, "...", "raise", "return", None),
        (check, "...", "return", None),
        (check, "...", "return", None),
    ):
        if exc1 is None and exc2 is not None:
            continue

        function_str = f"async def foo():\n  try:\n    {try_}\n"

        for arg, val in {
            "except ValueError": exc1,
            "except SyntaxError": exc2,
            "except": bare_exc,
            "else": else_,
            "finally": finally_,
        }.items():
            if val is not None:
                function_str += f"  {arg}:\n    {val}\n"

        try:
            tree = ast.parse(function_str)
        except Exception:
            assert exc1 is exc2 is bare_exc is None and (
                finally_ is None or else_ is not None
            )
            return

        errors = [e for e in Plugin(tree).run() if e.code == "TRIO107"]

        if (
            # return in exception
            "return" in (exc1, exc2, bare_exc)
            # exception and finally doesn't checkpoint, checkpoint in try might not run
            or ("..." in (exc1, exc2, bare_exc) and finally_ != check)
            # no checkpoints in normal control flow
            or check not in (try_, finally_, else_)
            # return in else|finally w/o checkpoint before
            or ("return" in (else_, finally_) and check not in (else_, try_))
            # return in finally with no bare exception, checkpoint in try might not run
            or (finally_ == "return" and bare_exc is None)
        ):
            assert errors, "# missing alarm:\n" + function_str
        else:
            assert not errors, "# false alarm:\n" + function_str


def test_114_raises_on_invalid_parameter(capsys: pytest.CaptureFixture[str]):
    plugin = Plugin(ast.AST())
    om = _default_option_manager()
    plugin.add_options(om)
    # flake8 will reraise ArgumentError as SystemExit
    for arg in "blah.foo", "foo*", "*":
        with pytest.raises(SystemExit):
            plugin.parse_options(
                om.parse_args(args=[f"--startable-in-context-manager={arg}"])
            )
        out, err = capsys.readouterr()
        assert not out
        assert f"{arg!r} is not a valid method identifier" in err


def test_200_options(capsys: pytest.CaptureFixture[str]):
    plugin = Plugin(ast.AST())
    om = _default_option_manager()
    plugin.add_options(om)
    for i, arg in (0, "foo"), (2, "foo->->bar"), (2, "foo->bar->fee"):
        with pytest.raises(SystemExit):
            plugin.parse_options(
                om.parse_args(args=[f"--trio200-blocking-calls={arg}"])
            )
        out, err = capsys.readouterr()
        assert not out
        assert all(word in err for word in (str(i), arg, "->"))


def test_from_config_file(tmp_path: Path):
    tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
trio200-blocking-calls =
  sync_fns.*->the_async_equivalent,
select = TRIO200
"""
    )
    tmp_path.joinpath("example.py").write_text(
        """
import sync_fns

async def foo():
    sync_fns.takes_a_long_time()
"""
    )
    res = subprocess.run(["flake8"], cwd=tmp_path, capture_output=True)
    assert not res.stderr
    assert res.stdout == (
        b"./example.py:5:5: TRIO200: User-configured blocking sync call sync_fns.* "
        b"in async function, consider replacing with the_async_equivalent.\n"
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

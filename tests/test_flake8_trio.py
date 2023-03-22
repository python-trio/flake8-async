"""Main test file for the plugin."""

from __future__ import annotations

import ast
import copy
import difflib
import itertools
import os
import re
import site
import sys
import tokenize
import unittest
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, DefaultDict

import libcst as cst
import pytest
from flake8 import __version_info__ as flake8_version_info
from flake8.options.manager import OptionManager
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

from flake8_trio import Plugin
from flake8_trio.base import Error, Statement
from flake8_trio.visitors import ERROR_CLASSES, ERROR_CLASSES_CST

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from flake8_trio.visitors.flake8triovisitor import Flake8TrioVisitor

AUTOFIX_DIR = Path(__file__).parent / "autofix_files"

test_files: list[tuple[str, Path]] = sorted(
    (f.stem.upper(), f) for f in (Path(__file__).parent / "eval_files").iterdir()
)
autofix_files: dict[str, Path] = {
    f.stem.upper(): f for f in AUTOFIX_DIR.iterdir() if f.suffix == ".py"
}
# check that there's an eval file for each autofix file
assert set(autofix_files.keys()) - {f[0] for f in test_files} == set()


class ParseError(Exception):
    ...


# flake8 6 added a required named parameter formatter_names
def _default_option_manager():
    kwargs = {}
    if flake8_version_info[0] >= 6:
        kwargs["formatter_names"] = ["default"]
    return OptionManager(version="", plugin_versions="", parents=[], **kwargs)


# check for presence of _pyXX, skip if version is later, and prune parameter
def check_version(test: str):
    python_version = re.search(r"(?<=_PY)\d*", test)
    if python_version:
        version_str = python_version.group()
        major, minor = version_str[0], version_str[1:]
        v_i = sys.version_info
        if (v_i.major, v_i.minor) < (int(major), int(minor)):
            pytest.skip(f"python version {v_i} smaller than {major}, {minor}")


# mypy does not see that both types have error_codes
ERROR_CODES: dict[str, Flake8TrioVisitor] = {
    err_code: err_class  # type: ignore[misc]
    for err_class in (*ERROR_CLASSES, *ERROR_CLASSES_CST)
    for err_code in err_class.error_codes.keys()  # type: ignore[attr-defined]
}


# difflib generates lots of lines with one trailing space, which is an eyesore
# and trips up pre-commit, git diffs, etc. If there actually was diff trailing
# space in the content it's picked up elsewhere and by pre-commit.
def strip_difflib_space(s: str) -> str:
    if s[-2:] == " \n":
        return s[:-2] + "\n"
    return s


def diff_strings(first: str, second: str, /) -> str:
    return "".join(
        map(
            strip_difflib_space,
            difflib.unified_diff(
                first.splitlines(keepends=True),
                second.splitlines(keepends=True),
            ),
        )
    )


# replaces all instances of `original` with `new` in string
# unless it's preceded by a `-`, which indicates it's part of a command-line flag
def replace_library(string: str, original: str = "trio", new: str = "anyio") -> str:
    return re.sub(rf"(?<!-){original}", new, string)


def check_autofix(
    test: str,
    plugin: Plugin,
    unfixed_code: str,
    generate_autofix: bool,
    anyio: bool = False,
):
    # the source code after it's been visited by current transformers
    visited_code = plugin.module.code

    if "# AUTOFIX" not in unfixed_code:
        assert unfixed_code == visited_code
        return

    # the full generated source code, saved from a previous run
    if test not in autofix_files:
        autofix_files[test] = AUTOFIX_DIR / (test.lower() + ".py")
        autofix_files[test].write_text("")
    previous_autofixed = autofix_files[test].read_text()

    # file contains a previous diff showing what's added/removed by the autofixer
    # i.e. a diff between "eval_files/{test}.py" and "autofix_files/{test}.py"
    autofix_diff_file = AUTOFIX_DIR / f"{test.lower()}.py.diff"
    if not autofix_diff_file.exists():
        assert generate_autofix, "autofix diff file doesn't exist"
        # if generate_autofix is set, the diff content isn't used and the file
        # content will be created
        autofix_diff_content = ""
    else:
        autofix_diff_content = autofix_diff_file.read_text()

    # if running against anyio, since "eval_files/{test.py}" have replaced trio->anyio,
    # meaning it's replaced in visited_code, we also replace it in previous generated code
    # and in the previous diff
    if anyio:
        previous_autofixed = replace_library(previous_autofixed)
        autofix_diff_content = replace_library(autofix_diff_content)

    # save any difference in the autofixed code
    diff = diff_strings(previous_autofixed, visited_code)

    # generate diff between unfixed and visited code, i.e. what's added/removed
    added_autofix_diff = diff_strings(unfixed_code, visited_code)

    # print diff, mainly helpful during development
    if diff:
        print("\n", diff)

    # if --generate-autofix is specified, which it may be during development,
    # just silently overwrite the content.
    if generate_autofix and not anyio:
        autofix_files[test].write_text(visited_code)
        autofix_diff_file.write_text(added_autofix_diff)
        return

    # assert that there's no difference in the autofixed code from before
    assert visited_code == previous_autofixed
    # and assert that the diff is the same, which it should be if the above passes
    assert added_autofix_diff == autofix_diff_content


@pytest.mark.parametrize(("test", "path"), test_files)
def test_eval(test: str, path: Path, generate_autofix: bool):
    content = path.read_text()
    if "# NOTRIO" in content:
        pytest.skip("file marked with NOTRIO")

    expected, parsed_args = _parse_eval_file(test, content)
    parsed_args.append("--autofix")
    if "# TRIO_NO_ERROR" in content:
        expected = []

    plugin = Plugin.from_source(content)
    _ = assert_expected_errors(plugin, *expected, args=parsed_args)

    check_autofix(test, plugin, content, generate_autofix)


@pytest.mark.parametrize(("test", "path"), test_files)
def test_eval_anyio(test: str, path: Path, generate_autofix: bool):
    # read content, replace instances of trio with anyio, and write to tmp_file
    content = path.read_text()

    if "# NOANYIO" in content:
        pytest.skip("file marked with NOANYIO")

    # if test is marked NOTRIO, it's not written to require substitution
    if "# NOTRIO" not in content:
        content = replace_library(content)

        # if substituting we're messing up columns
        ignore_column = True
    else:
        ignore_column = False

    # parse args and expected errors
    expected, parsed_args = _parse_eval_file(test, content)

    parsed_args.insert(0, "--anyio")
    parsed_args.append("--autofix")

    # initialize plugin and check errors, ignoring columns since they occasionally are
    # wrong due to len("anyio") > len("trio")
    plugin = Plugin.from_source(content)

    if "# ANYIO_NO_ERROR" in content:
        expected = []

    errors = assert_expected_errors(
        plugin, *expected, args=parsed_args, ignore_column=ignore_column
    )

    # check that error messages refer to 'anyio', or to neither library
    for error in errors:
        message = error.message.format(*error.args)
        assert "anyio" in message or "trio" not in message

    check_autofix(test, plugin, content, generate_autofix, anyio=True)


# check that autofixed files raise no errors and doesn't get autofixed (again)
@pytest.mark.parametrize("test", autofix_files)
def test_autofix(test: str):
    content = autofix_files[test].read_text()
    if "# NOTRIO" in content:
        pytest.skip("file marked with NOTRIO")

    _, parsed_args = _parse_eval_file(test, content)
    parsed_args.append("--autofix")

    plugin = Plugin.from_source(content)
    # not passing any expected errors
    _ = assert_expected_errors(plugin, args=parsed_args)

    diff = diff_strings(plugin.module.code, content)
    if diff:
        print(diff)
    assert plugin.module.code == content, "autofixed file changed when autofixed again"


def _parse_eval_file(test: str, content: str) -> tuple[list[Error], list[str]]:
    # version check
    check_version(test)
    test = test.split("_")[0]

    parsed_args = []

    # only enable the tested visitor to save performance and ease debugging
    # if a test requires enabling multiple visitors they specify a
    # `# ARG --enable-vis...` that comes later in the arg list, overriding this
    visitor_codes_regex = ""
    if test in ERROR_CODES:
        parsed_args = [f"--enable-visitor-codes-regex={test}"]
        visitor_codes_regex = f"{test}"

    expected: list[Error] = []

    for lineno, line in enumerate(content.split("\n"), start=1):
        # interpret '\n' in comments as actual newlines
        line = line.replace("\\n", "\n")

        line = line.strip()

        # add command-line args if specified with #ARG
        if reg_match := re.search(r"(?<=ARG ).*", line):
            argument = reg_match.group().strip()
            parsed_args.append(argument)
            if m := re.match(r"--enable-visitor-codes-regex=(.*)", argument):
                visitor_codes_regex = m.groups()[0]

        # skip commented out lines
        if not line or line[0] == "#":
            continue

        # get text between `error:` and (end of line or another comment)
        k = re.findall(r"(error|TRIO...)(_.*)?:([^#]*)(?=#|$)", line)

        for err_code, alt_code, err_args in k:
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
            ), f"invalid column {col!r} @L{lineno}, in {line!r}"

            if err_code == "error":
                err_code = test
            error_class = ERROR_CODES[err_code + alt_code]
            message = error_class.error_codes[err_code + alt_code]
            try:
                expected.append(Error(err_code, lineno, int(col), message, *args))
            except AttributeError as e:
                msg = f'Line {lineno}: Failed to format\n {message!r}\n"with\n{args}'
                raise ParseError(msg) from e

    assert visitor_codes_regex, "no visitors enabled"
    for error in expected:
        assert re.match(
            visitor_codes_regex, error.code
        ), "Expected error code not enabled"

    return expected, parsed_args


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
    "TRIO117",
    "TRIO118",
}


class SyncTransformer(ast.NodeTransformer):
    def visit_Await(self, node: ast.Await):
        return self.generic_visit(node.value)

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


@pytest.mark.parametrize(("test", "path"), test_files)
def test_noerror_on_sync_code(test: str, path: Path):
    if any(e in test for e in error_codes_ignored_when_checking_transformed_sync_code):
        return
    with tokenize.open(path) as f:
        source = f.read()
    tree = SyncTransformer().visit(ast.parse(source))

    ignored_codes_regex = (
        "(?!("
        + "|".join(error_codes_ignored_when_checking_transformed_sync_code)
        + "))"
    )
    _ = assert_expected_errors(
        Plugin(tree, [ast.unparse(tree)]),
        args=[f"--enable-visitor-codes-regex={ignored_codes_regex}"],
    )


def initialize_options(plugin: Plugin, args: list[str] | None = None):
    om = _default_option_manager()
    plugin.add_options(om)
    plugin.parse_options(om.parse_args(args=(args if args else [])))


def assert_expected_errors(
    plugin: Plugin,
    *expected: Error,
    args: list[str] | None = None,
    ignore_column: bool = False,
) -> list[Error]:
    # initialize default option values
    initialize_options(plugin, args)

    errors = sorted(e for e in plugin.run())
    expected_ = sorted(expected)

    if ignore_column:
        for e in *errors, *expected_:
            e.col = -1

    print_first_diff(errors, expected_)
    assert_correct_lines_and_codes(errors, expected_)
    if not ignore_column:
        assert_correct_attribute(errors, expected_, "col")
    assert_correct_attribute(errors, expected_, "message")
    assert_correct_attribute(errors, expected_, "args")

    # full check
    assert errors == expected_

    # test tuple conversion and iter types
    assert_tuple_and_types(errors, expected_)

    return errors


def print_first_diff(errors: Sequence[Error], expected: Sequence[Error]):
    first_error_line: list[Error] = []
    first_expected_line: list[Error] = []
    for err, exp in zip(errors, expected):
        if err == exp:
            continue
        if not first_error_line or err.line == first_error_line[0].line:
            first_error_line.append(err)
        if not first_expected_line or exp.line == first_expected_line[0].line:
            first_expected_line.append(exp)

    if first_expected_line != first_error_line:
        print(
            "\nFirst lines with different errors",
            f"  actual: {[e.cmp() for e in first_error_line]}",
            f"expected: {[e.cmp() for e in first_expected_line]}",
            "",
            sep="\n",
            file=sys.stderr,
        )


def assert_correct_lines_and_codes(errors: Iterable[Error], expected: Iterable[Error]):
    """Check that errors are on correct lines."""
    MyDict = DefaultDict[int, DefaultDict[str, int]]  # TypeAlias

    all_lines = sorted({e.line for e in (*errors, *expected)})

    error_dict: MyDict = DefaultDict(lambda: DefaultDict(int))
    expected_dict = copy.deepcopy(error_dict)

    # populate dicts with number of errors per line
    for e in errors:
        error_dict[e.line][e.code] += 1
    for e in expected:
        expected_dict[e.line][e.code] += 1

    error_count = 0
    for line in all_lines:
        if error_dict[line] == expected_dict[line]:
            continue

        # go through all the codes on the line
        for code in sorted({*error_dict[line], *expected_dict[line]}):
            if error_count == 0:
                print(
                    "Lines with different # of errors:",
                    "-" * 38,
                    f"| line | {'code':7} | actual | expected |",
                    sep="\n",
                    file=sys.stderr,
                )

            print(
                f"| {line:4}",
                f"{code}",
                f"{error_dict[line][code]:6}",
                f"{expected_dict[line][code]:8} |",
                sep=" | ",
                file=sys.stderr,
            )
            error_count += abs(error_dict[line][code] - expected_dict[line][code])
    assert error_count == 0


def assert_correct_attribute(
    errors: Iterable[Error], expected: Iterable[Error], attribute: str
):
    # check errors have correct messages
    args_error = False
    for err, exp in zip(errors, expected):
        assert (err.line, err.code) == (exp.line, exp.code), "error in previous checks"
        errattr = getattr(err, attribute)
        expattr = getattr(exp, attribute)
        if errattr != expattr:
            if not args_error:
                print(
                    f"Errors with different {attribute}:",
                    "-" * 20,
                    sep="\n",
                    file=sys.stderr,
                )
                args_error = True
            print(
                f"*    line: {err.line:3} differs\n",
                f"  actual: {errattr}\n",
                f"expected: {expattr}\n",
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
                f"format string: {ERROR_CODES[error.code].error_codes[error.code]!r}",
                sep="\n    ",
                file=sys.stderr,
            )
            raise

    for err, exp in zip(errors, expected):
        err_msg = info_tuple(err)
        for err, type_ in zip(err_msg, (int, int, str, type(None))):
            assert isinstance(err, type_)
        assert err_msg == info_tuple(exp)


@pytest.mark.fuzz()
def test_910_permutations():
    """Tests all possible permutations for TRIO910.

    Since each test is so fast, and there's so many permutations, manually doing
    the permutations in a single test is much faster than the permutations from using
    pytest parametrization - and does not clutter up the output massively.

    generates code that looks like this, where a block content of `None` means the
    block is excluded:

    async def foo():
        try:
            await foo() | ...
        except ValueError:
            await foo() | ... | raise | return | None
        except SyntaxError:
            await foo() | ... | raise | return | None
        except:
            await foo() | ... | raise | return | None
        else:
            await foo() | ... | return | None
        finally:
            await foo() | ... | return | None
    """
    plugin = Plugin(ast.AST(), [])
    initialize_options(plugin, args=["--enable-visitor-codes-regex=TRIO910"])

    check = "await foo()"

    # loop over all the possible content of the different blocks
    for try_, exc1, exc2, bare_exc, else_, finally_ in itertools.product(
        (check, "..."),  # try_
        (check, "...", "raise", "return", None),  # exc1
        (check, "...", "raise", "return", None),  # exc2
        (check, "...", "raise", "return", None),  # bare_exc
        (check, "...", "return", None),  # else_
        (check, "...", "return", None),  # finally_
    ):
        # exclude duplicate tests where there's a second exception block but no first
        if exc1 is None and exc2 is not None:
            continue

        # syntax error if there's no exception block but there's finally and/or else
        if exc1 is exc2 is bare_exc is None and (finally_ is None or else_ is not None):
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

        module = cst.parse_module(function_str)

        # not a type error per se, but it's pyright warning about assigning to a
        # protected class member - hence we silence it with a `type: ignore`.
        plugin._module = module  # type: ignore
        errors = list(plugin.run())

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


# from https://docs.python.org/3/library/itertools.html#itertools-recipes
def consume(iterator: Iterable[Any]):
    deque(iterator, maxlen=0)


@pytest.mark.fuzz()
class TestFuzz(unittest.TestCase):
    @settings(max_examples=1_000, suppress_health_check=[HealthCheck.too_slow])
    @given((from_grammar() | from_node()).map(ast.parse))
    def test_does_not_crash_on_any_valid_code(self, syntax_tree: ast.AST):
        # TODO: figure out how to get unittest to play along with pytest options
        # so `--enable-visitor-codes-regex` can be passed through.
        # Though I barely notice a difference manually changing this value, or even
        # not running the plugin at all, so overhead looks to be vast majority of runtime
        enable_visitor_codes_regex = ".*"

        # Given any syntatically-valid source code, the checker should
        # not crash.  This tests doesn't check that we do the *right* thing,
        # just that we don't crash on valid-if-poorly-styled code!
        plugin = Plugin(syntax_tree, [ast.unparse(syntax_tree)])
        initialize_options(
            plugin, [f"--enable-visitor-codes-regex={enable_visitor_codes_regex}"]
        )

        consume(plugin.run())


def _iter_python_files():
    # Because the generator isn't perfect, we'll also test on all the code
    # we can easily find in our current Python environment - this includes
    # the standard library, and all installed packages.
    for base in sorted(set(site.PREFIXES)):
        for dirname, _, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    yield Path(dirname) / f


@pytest.mark.fuzz()
def test_does_not_crash_on_site_code(enable_visitor_codes_regex: str):
    for path in _iter_python_files():
        try:
            plugin = Plugin.from_filename(str(path))
            initialize_options(
                plugin, [f"--enable-visitor-codes-regex={enable_visitor_codes_regex}"]
            )
            consume(plugin.run())
        except Exception as err:
            raise AssertionError(f"Failed on {path}") from err

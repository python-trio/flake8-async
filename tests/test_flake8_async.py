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
from argparse import ArgumentParser
from collections import defaultdict, deque
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any

import libcst as cst
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesmith import from_grammar, from_node

from flake8_async import Plugin
from flake8_async.base import Error, Statement
from flake8_async.visitors import ERROR_CLASSES, ERROR_CLASSES_CST
from flake8_async.visitors.visitor4xx import EXCGROUP_ATTRS

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from flake8_async.visitors.flake8asyncvisitor import Flake8AsyncVisitor

AUTOFIX_DIR = Path(__file__).parent / "autofix_files"


test_files: list[tuple[str, Path]] = sorted(
    (f.stem.upper(), f) for f in (Path(__file__).parent / "eval_files").iterdir()
)
autofix_files: dict[str, Path] = {
    f.stem.upper(): f for f in AUTOFIX_DIR.iterdir() if f.suffix == ".py"
}
# check that there's an eval file for each autofix file
extra_autofix_files = set(autofix_files.keys()) - {f[0] for f in test_files}
assert (
    extra_autofix_files == set()
), f"no eval file for autofix file[s] {extra_autofix_files}"


class ParseError(Exception): ...


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
ERROR_CODES: dict[str, Flake8AsyncVisitor] = {
    err_code: err_class  # type: ignore[misc]
    for err_class in (*ERROR_CLASSES, *ERROR_CLASSES_CST)
    for err_code in err_class.error_codes  # type: ignore[attr-defined]
}


def format_difflib_line(s: str) -> str:
    # replace line markers with x's, to not generate massive diffs when lines get moved
    s = re.sub(r"(?<= )[+-]\d*(?=,)", "x", s)

    # difflib generates lots of lines with one trailing space, which is an eyesore
    # and trips up pre-commit, git diffs, etc. If there actually was diff trailing
    # space in the content it's picked up elsewhere and by pre-commit.
    if s[-2:] == " \n":
        return s[:-2] + "\n"
    return s


def diff_strings(first: str, second: str, /) -> str:
    if first == second:
        return ""
    return (
        "".join(
            map(
                format_difflib_line,
                difflib.unified_diff(
                    first.splitlines(keepends=True),
                    second.splitlines(keepends=True),
                ),
            )
        ).rstrip("\n")
        + "\n"
    )
    # make sure only single newline at end of file


# replaces all instances of `original` with `new` in string
# unless it's preceded by a `-`, which indicates it's part of a command-line flag
def replace_library(string: str, original: str = "trio", new: str = "anyio") -> str:
    def replace_str(string: str, original: str, new: str) -> str:
        return re.sub(rf"(?<!-){original}", new, string)

    # this isn't super pretty, and doesn't include asyncio.TaskGroup(),
    # and could probably cover more methods, but /shrug
    replacements: tuple[tuple[str, str], ...] = (
        ("open_nursery", "create_task_group"),
        ('"nursery"', '"task group"'),  # in error messages
        ("nursery", "task_group"),
        ("Nursery", "TaskGroup"),
    )

    if sorted((original, new)) == ["anyio", "trio"]:
        for trio_, anyio_ in replacements:
            if original == "trio":
                from_ = trio_
                to_ = anyio_
            else:
                from_ = anyio_
                to_ = trio_
            string = replace_str(string, from_, to_)
    return replace_str(string, original, new)


def check_autofix(
    test: str,
    plugin: Plugin,
    unfixed_code: str,
    generate_autofix: bool,
    magic_markers: MagicMarkers,
    library: str = "trio",
):
    base_library = magic_markers.BASE_LIBRARY
    # the source code after it's been visited by current transformers
    visited_code = plugin.module.code

    # if the file is specifically marked with NOAUTOFIX, that means it has visitors
    # that will autofix with --autofix, but the file explicitly doesn't want to check
    # the result of doing that. THIS IS DANGEROUS
    assert not (magic_markers.AUTOFIX and magic_markers.NOAUTOFIX)
    if magic_markers.NOAUTOFIX:
        print(f"eval file {test} marked with dangerous marker NOAUTOFIX")
        return

    if (
        # not marked for autofixing
        not magic_markers.AUTOFIX
        # file+library does not raise errors
        or magic_markers.library_no_error(library)
        # code raises errors on asyncio, but does not support autofixing for it
        or (library == "asyncio" and magic_markers.ASYNCIO_NO_AUTOFIX)
    ):
        assert (
            unfixed_code == visited_code
        ), "Code changed after visiting, but magic markers say it shouldn't change."
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
        assert generate_autofix, f"autofix diff file {autofix_diff_file} doesn't exist"
        # if generate_autofix is set, the diff content isn't used and the file
        # content will be created
        autofix_diff_content = ""
    else:
        autofix_diff_content = autofix_diff_file.read_text()

    # if running against anyio, since "eval_files/{test.py}" have replaced trio->anyio,
    # meaning it's replaced in visited_code, we also replace it in previous generated code
    # and in the previous diff
    if base_library != library:
        previous_autofixed = replace_library(
            previous_autofixed, original=base_library, new=library
        )
        autofix_diff_content = replace_library(
            autofix_diff_content, original=base_library, new=library
        )

    # save any difference in the autofixed code
    diff = diff_strings(previous_autofixed, visited_code)

    # generate diff between unfixed and visited code, i.e. what's added/removed
    added_autofix_diff = diff_strings(unfixed_code, visited_code)

    # print diff, mainly helpful during development
    if diff.strip():
        print("\n", diff)

    # if --generate-autofix is specified, which it may be during development,
    # just silently overwrite the content.
    if generate_autofix and base_library == library:
        autofix_files[test].write_text(visited_code)
        autofix_diff_file.write_text(added_autofix_diff)
        return

    # assert that there's no difference in the autofixed code from before
    assert visited_code == previous_autofixed, (
        "autofix diff, run with --generate-autofix if the test file has changed to"
        " update the autofix files."
    )
    # and assert that the diff is the same, which it should be if the above passes
    assert added_autofix_diff == autofix_diff_content, (
        "THIS SHOULD NOT HAPPEN: diff in the autofix diff - without there being a diff"
        " in the autofixed code, run with --generate-autofix if the test file has"
        " changed to update the autofix files."
    )


# This can be further cleaned up by adding the other return values from
# parse_eval_file (Errors, args and enabled_codes) to this class - and find magic
# markers in the same pass as we parse out errors etc.
@dataclass
class MagicMarkers:
    # Exclude checking a library against a file
    NOANYIO: bool = False
    NOTRIO: bool = False
    NOASYNCIO: bool = False
    # File should raise no errors with this library
    ANYIO_NO_ERROR: bool = False
    TRIO_NO_ERROR: bool = False
    ASYNCIO_NO_ERROR: bool = False

    AUTOFIX: bool = False
    NOAUTOFIX: bool = False

    # File should not get modified when running with asyncio+autofix
    ASYNCIO_NO_AUTOFIX: bool = False
    # eval file is written using this library, so no substitution is required
    BASE_LIBRARY: str = "trio"

    def library_no_error(self, library: str) -> bool:
        return {
            "anyio": self.ANYIO_NO_ERROR,
            "asyncio": self.ASYNCIO_NO_ERROR,
            "trio": self.TRIO_NO_ERROR,
        }[library]


def find_magic_markers(
    content: str,
) -> MagicMarkers:
    found_markers = MagicMarkers()
    markers = (f.name for f in fields(found_markers))
    pattern = rf'# ({"|".join(markers)})'
    for f in re.findall(pattern, content):
        if f == "BASE_LIBRARY":
            m = re.search(r"# BASE_LIBRARY (\w*)", content)
            assert m, "invalid 'BASE_LIBRARY' marker"
            found_markers.BASE_LIBRARY = m.groups()[0]
        else:
            setattr(found_markers, f, True)
    return found_markers


# Caching test file content makes ~0 difference to runtime
@pytest.mark.parametrize("noqa", [False, True], ids=["normal", "noqa"])
@pytest.mark.parametrize("autofix", [False, True], ids=["noautofix", "autofix"])
@pytest.mark.parametrize("library", ["trio", "anyio", "asyncio"])
@pytest.mark.parametrize(("test", "path"), test_files, ids=[f[0] for f in test_files])
def test_eval(
    test: str,
    path: Path,
    autofix: bool,
    library: str,
    noqa: bool,
    generate_autofix: bool,
):
    content = path.read_text()
    magic_markers = find_magic_markers(content)

    # if autofixing, columns may get messed up
    ignore_column = autofix
    only_check_not_crash = False

    # file would raise different errors if transformed to a different library
    # so we run the checker against it solely to check that it doesn't crash
    if (
        (library == "anyio" and magic_markers.NOANYIO)
        or (library == "asyncio" and magic_markers.NOASYNCIO)
        or (library == "trio" and magic_markers.NOTRIO)
    ):
        only_check_not_crash = True

    if library != magic_markers.BASE_LIBRARY:
        content = replace_library(
            content, original=magic_markers.BASE_LIBRARY, new=library
        )

        # if substituting we're messing up columns
        ignore_column = True

    if noqa:
        # replace all instances of some error with noqa
        content = re.sub(r"#[\s]*(error|ASYNC\d\d\d):.*", "# noqa", content)

    expected, parsed_args, enable = _parse_eval_file(
        test, content, only_check_not_crash=only_check_not_crash
    )
    if library != "trio":
        parsed_args.insert(0, f"--{library}")
    if autofix:
        parsed_args.append(f"--autofix={enable}")

    if (
        (library == "anyio" and magic_markers.ANYIO_NO_ERROR)
        or (library == "trio" and magic_markers.TRIO_NO_ERROR)
        or (library == "asyncio" and magic_markers.ASYNCIO_NO_ERROR)
    ):
        expected = []

    plugin = Plugin.from_source(content)
    errors = assert_expected_errors(
        plugin,
        *expected,
        args=parsed_args,
        ignore_column=ignore_column,
        only_check_not_crash=only_check_not_crash,
        noqa=noqa,
    )

    if only_check_not_crash:
        # mark it as skipped to indicate we didn't actually test anything in particular
        # (it confused me once when I didn't notice a file was marked with NOTRIO)
        pytest.skip()

    # Check that error messages refer to current library, or to no library.
    if test not in (
        # 103_[BOTH/ALL]_IMPORTED will contain messages that refer to anyio regardless of
        # current library
        "ASYNC103_BOTH_IMPORTED",
        "ASYNC103_ALL_IMPORTED",
        # 23X_asyncio messages does not mention asyncio
        "ASYNC23X_ASYNCIO",
    ):
        for error in errors:
            message = error.message.format(*error.args)
            assert library in message or not any(
                lib in message for lib in ("anyio", "asyncio", "trio")
            )

    if autofix and not noqa:
        check_autofix(
            test,
            plugin,
            content,
            generate_autofix,
            library=library,
            magic_markers=magic_markers,
        )
    else:
        # make sure content isn't modified
        assert content == plugin.module.code


# check that autofixed files raise no errors and doesn't get autofixed (again)
@pytest.mark.parametrize("test", autofix_files)
def test_autofix(test: str):
    content = autofix_files[test].read_text()
    assert content, "empty file"

    if "# NOTRIO" in content:
        pytest.skip("file marked with NOTRIO")

    _, parsed_args, enable = _parse_eval_file(test, content)
    parsed_args.append(f"--autofix={enable}")

    plugin = Plugin.from_source(content)
    # not passing any expected errors
    _ = assert_expected_errors(plugin, args=parsed_args)

    diff = diff_strings(plugin.module.code, content)
    if diff.strip():
        print(diff)
    assert plugin.module.code == content, "autofixed file changed when autofixed again"


def _parse_eval_file(
    test: str, content: str, only_check_not_crash: bool = False
) -> tuple[list[Error], list[str], str]:
    # version check
    check_version(test)
    test = test.split("_")[0]

    parsed_args = []

    # Only enable the tested visitor to save performance and ease debugging.
    # If a test requires enabling multiple visitors they specify a
    # `# ARG --enable=` that comes later in the arg list, overriding this.
    enabled_codes = ""
    if test in ERROR_CODES:
        parsed_args = [f"--enable={test}"]
        enabled_codes = f"{test}"

    expected: list[Error] = []

    for lineno, line in enumerate(content.split("\n"), start=1):
        # interpret '\n' in comments as actual newlines
        line = line.replace("\\n", "\n")

        line = line.strip()

        # add command-line args if specified with #ARG
        if reg_match := re.search(r"(?<=ARG ).*", line):
            argument = reg_match.group().strip()
            parsed_args.append(argument)
            if m := re.match(r"--enable=(.*)", argument):
                enabled_codes = m.groups()[0]

        # skip commented out lines
        if not line or line[0] == "#":
            continue

        # skip lines that *don't* have a comment
        if "#" not in line:
            continue

        # get text between `error:` and (end of line or another comment)
        k = re.findall(r"(error|ASYNC...)(_.*)?:([^#]*)(?=#|$)", line)

        for err_code, alt_code, err_args in k:
            try:
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
            if only_check_not_crash and err_code + alt_code not in ERROR_CODES:
                continue
            error_class = ERROR_CODES[err_code + alt_code]
            message = error_class.error_codes[err_code + alt_code]
            try:
                expected.append(Error(err_code, lineno, int(col), message, *args))
            except AttributeError as e:
                msg = f"Line {lineno}: Failed to format\n {message!r}\nwith\n{args}"
                raise ParseError(msg) from e

    assert enabled_codes, "no codes enabled. Fix file name or add `# ARG --enable=...`"
    enabled_codes_list = enabled_codes.split(",")
    for code in enabled_codes_list:
        assert re.fullmatch(
            r"ASYNC\d\d\d", code
        ), f"invalid code {code} in list {enabled_codes_list}"

    for error in expected:
        for code in enabled_codes.split(","):
            if error.code.startswith(code):
                break
        else:
            assert (
                error.code in enabled_codes_list
            ), f"Expected error code {error.code} not enabled"

    return expected, parsed_args, enabled_codes


# Codes that are supposed to also raise errors when run on sync code, and should
# be excluded from the SyncTransformer check.
# Expand this list when adding a new check if it does not care about whether the code
# is asynchronous or not.
error_codes_ignored_when_checking_transformed_sync_code = {
    "ASYNC100",
    "ASYNC101",
    "ASYNC103",
    "ASYNC104",
    "ASYNC105",
    "ASYNC106",
    "ASYNC111",
    "ASYNC112",
    "ASYNC115",
    "ASYNC116",
    "ASYNC117",
    "ASYNC118",
    # opening nurseries & taskgroups can only be done in async context, so ASYNC121
    # doesn't check for it
    "ASYNC121",
    "ASYNC122",
    "ASYNC123",
    "ASYNC125",
    "ASYNC300",
    "ASYNC400",
    "ASYNC912",
}


class SyncTransformer(ast.NodeTransformer):
    def visit_Await(self, node: ast.Await):
        return self.generic_visit(node.value)

    def replace_async(
        self, node: ast.AST, target: type[ast.AST], *args: object
    ) -> ast.AST:
        node = self.generic_visit(node)
        # py313 gives DeprecationWarning if missing posargs, so we pass them even if we
        # overwrite __dict__ directly afterwards
        newnode = target(*args)
        newnode.__dict__ = node.__dict__
        return newnode

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        return self.replace_async(node, ast.FunctionDef, node.name, node.args)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        return self.replace_async(node, ast.With)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        return self.replace_async(node, ast.For, node.target, node.iter)


@pytest.mark.parametrize(("test", "path"), test_files, ids=[f[0] for f in test_files])
def test_noerror_on_sync_code(test: str, path: Path):
    if any(e in test for e in error_codes_ignored_when_checking_transformed_sync_code):
        return
    check_version(test)
    with tokenize.open(path) as f:
        source = f.read()
    tree = SyncTransformer().visit(ast.parse(source))

    _ = assert_expected_errors(
        Plugin(tree, [ast.unparse(tree)]),
        args=[
            "--disable="
            + ",".join(error_codes_ignored_when_checking_transformed_sync_code)
        ],
    )


def initialize_options(plugin: Plugin, args: list[str] | None = None):
    parser = ArgumentParser(prog="flake8-async")
    Plugin.add_options(parser)
    Plugin.parse_options(parser.parse_args(args))


def assert_expected_errors(
    plugin: Plugin,
    *expected: Error,
    args: list[str] | None = None,
    ignore_column: bool = False,
    only_check_not_crash: bool = False,
    noqa: bool = False,
) -> list[Error]:
    # initialize default option values
    initialize_options(plugin, args)

    errors = sorted(e for e in plugin.run())
    expected_ = sorted(expected)

    if ignore_column:
        for e in *errors, *expected_:
            e.col = -1

    if only_check_not_crash:
        assert noqa or errors != [], (
            "eval file giving no errors w/ only_check_not_crash, "
            "consider adding [library]NOERROR"
        )
        # Check that this file in fact does report different errors.
        assert errors != expected_ or (errors == expected_ == [] and noqa), (
            "eval file appears to give all the correct errors."
            " Maybe you can remove the `# NO[ANYIO/TRIO/ASYNCIO]` magic marker?"
        )
        return errors

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
    all_lines = sorted({e.line for e in (*errors, *expected)})

    error_dict: defaultdict[int, defaultdict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    expected_dict = copy.deepcopy(error_dict)

    # populate dicts with number of errors per line
    for e in errors:
        error_dict[e.line][e.code] += 1
    for e in expected:
        expected_dict[e.line][e.code] += 1

    error_count = 0
    printed_header = False
    for line in all_lines:
        if error_dict[line] == expected_dict[line]:
            continue

        # go through all the codes on the line
        for code in sorted({*error_dict[line], *expected_dict[line]}):
            if not printed_header:
                print(
                    "Lines with different # of errors:",
                    "-" * 38,
                    f"| line | {'code':8} | actual | expected |",
                    sep="\n",
                    file=sys.stderr,
                )
                printed_header = True

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
            # mypy fails to track types across the zip
            assert isinstance(err, type_)  # type: ignore[arg-type]
        assert err_msg == info_tuple(exp)


# eval_files tests check that noqa is respected when running as standalone, but
# they don't check anything when running as plugin.
# When run as a plugin, flake8 will handle parsing of `noqa`.
def test_noqa_respected_depending_on_standalone():
    text = """import trio
with trio.move_on_after(10): ... # noqa
"""
    plugin = Plugin.from_source(text)
    initialize_options(plugin, args=["--enable=ASYNC100"])

    assert plugin.standalone
    assert not tuple(plugin.run())

    plugin.standalone = False
    assert len(tuple(plugin.run())) == 1


# TODO: failing test due to issue #193
# the != in the assert should be a ==
def test_line_numbers_match_end_result():
    text = """import trio
with trio.move_on_after(10):
  ...

trio.sleep(0)
"""
    plugin = Plugin.from_source(text)
    initialize_options(
        plugin, args=["--enable=ASYNC100,ASYNC115", "--autofix=ASYNC100"]
    )
    errors = tuple(plugin.run())
    assert errors[1].line != plugin.module.code.split("\n").index("trio.sleep(0)") + 1


@pytest.mark.fuzz
def test_910_permutations():
    """Tests all possible permutations for ASYNC910.

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
    initialize_options(plugin, args=["--enable=ASYNC910"])

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

        plugin.module = module
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


def test_async400_excgroup_attributes():
    for attr in dir(ExceptionGroup):
        if attr.startswith("__") and attr.endswith("__"):
            continue
        assert attr in EXCGROUP_ATTRS


# from https://docs.python.org/3/library/itertools.html#itertools-recipes
def consume(iterator: Iterable[Any]):
    deque(iterator, maxlen=0)


@pytest.mark.fuzz
class TestFuzz(unittest.TestCase):
    @settings(
        max_examples=1_000, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    @given((from_grammar() | from_node()).map(ast.parse))
    def test_does_not_crash_on_any_valid_code(self, syntax_tree: ast.AST):
        # TODO: figure out how to get unittest to play along with pytest options
        # so `--enable-codes` can be passed through.
        # Though I barely notice a difference manually changing this value, or even
        # not running the plugin at all, so overhead looks to be vast majority of runtime
        enabled_codes = "ASYNC"

        # Given any syntatically-valid source code, the checker should
        # not crash.  This tests doesn't check that we do the *right* thing,
        # just that we don't crash on valid-if-poorly-styled code!
        plugin = Plugin(syntax_tree, [ast.unparse(syntax_tree)])
        initialize_options(plugin, [f"--enable={enabled_codes}"])

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


@pytest.mark.fuzz
def test_does_not_crash_on_site_code(enable_codes: str):
    for path in _iter_python_files():
        try:
            plugin = Plugin.from_filename(str(path))
            initialize_options(plugin, [f"--enable={enable_codes}"])
            consume(plugin.run())
        except Exception as err:  # noqa: PERF203 # try-except in loop
            raise AssertionError(f"Failed on {path}") from err

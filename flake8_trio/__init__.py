"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

from __future__ import annotations

import ast
import functools
import keyword
import os
import re
import subprocess
import sys
import tokenize
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import TYPE_CHECKING

import libcst as cst

from .runner import Flake8TrioRunner, Flake8TrioRunner_cst
from .visitors import default_disabled_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from os import PathLike

    from flake8.options.manager import OptionManager

    from .base import Error


# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "23.2.5"


# taken from https://github.com/Zac-HD/shed
@functools.lru_cache
def _get_git_repo_root(cwd: str | None = None) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        timeout=10,
        capture_output=True,
        text=True,
        cwd=cwd,
    ).stdout.strip()


@functools.cache
def _should_format(fname: str) -> bool:
    return fname.endswith((".py",))


# Enable support in libcst for new grammar
# See e.g. https://github.com/Instagram/LibCST/issues/862
# wrapping the call and restoring old values in case there's other libcst parsers
# in the same environment, which we don't wanna mess up.
def cst_parse_module_native(source: str) -> cst.Module:
    var = os.environ.get("LIBCST_PARSER_TYPE")
    try:
        os.environ["LIBCST_PARSER_TYPE"] = "native"
        mod = cst.parse_module(source)
    finally:
        del os.environ["LIBCST_PARSER_TYPE"]
        if var is not None:  # pragma: no cover
            os.environ["LIBCST_PARSER_TYPE"] = var
    return mod


def main() -> int:
    parser = ArgumentParser(prog="flake8_trio")
    parser.add_argument(
        nargs="*",
        metavar="file",
        dest="files",
        help="Files(s) to format, instead of autodetection.",
    )
    Plugin.add_options(parser)
    args = parser.parse_args()
    Plugin.parse_options(args)
    if args.files:
        # TODO: go through subdirectories if directory/ies specified
        all_filenames = args.files
    else:
        # Get all tracked files from `git ls-files`
        try:
            root = os.path.relpath(_get_git_repo_root())
            all_filenames = subprocess.run(
                ["git", "ls-files"],
                check=True,
                timeout=10,
                stdout=subprocess.PIPE,
                text=True,
                cwd=root,
            ).stdout.splitlines()
        except (subprocess.SubprocessError, FileNotFoundError):
            print(
                "Doesn't seem to be a git repo; pass filenames to format.",
                file=sys.stderr,
            )
            return 1
        all_filenames = [
            os.path.join(root, f) for f in all_filenames if _should_format(f)
        ]
    any_error = False
    for file in all_filenames:
        plugin = Plugin.from_filename(file)
        for error in sorted(plugin.run()):
            print(f"{file}:{error}")
            any_error = True
        if plugin.options.autofix:
            with open(file, "w") as file:
                file.write(plugin.module.code)
    return 1 if any_error else 0


class Plugin:
    name = __name__
    version = __version__
    options: Namespace = Namespace()

    def __init__(self, tree: ast.AST, lines: Sequence[str]):
        super().__init__()
        self._tree = tree
        source = "".join(lines)

        self.module: cst.Module = cst_parse_module_native(source)

    @classmethod
    def from_filename(cls, filename: str | PathLike[str]) -> Plugin:  # pragma: no cover
        # only used with --runslow
        with tokenize.open(filename) as f:
            source = f.read()
        return cls.from_source(source)

    # alternative `__init__` to avoid re-splitting and/or re-joining lines
    @classmethod
    def from_source(cls, source: str) -> Plugin:
        plugin = Plugin.__new__(cls)
        super(Plugin, plugin).__init__()
        plugin._tree = ast.parse(source)
        plugin.module = cst_parse_module_native(source)
        return plugin

    def run(self) -> Iterable[Error]:
        yield from Flake8TrioRunner.run(self._tree, self.options)
        cst_runner = Flake8TrioRunner_cst(self.options, self.module)
        yield from cst_runner.run()
        self.module = cst_runner.module

    @staticmethod
    def add_options(option_manager: OptionManager | ArgumentParser):
        if isinstance(option_manager, ArgumentParser):
            # TODO: disable TRIO9xx calls by default
            # if run as standalone
            add_argument = option_manager.add_argument
        else:  # if run as a flake8 plugin
            # Disable TRIO9xx calls by default
            option_manager.extend_default_ignore(default_disabled_error_codes)
            # add parameter to parse from flake8 config
            add_argument = functools.partial(  # type: ignore
                option_manager.add_option, parse_from_config=True
            )
        add_argument("--autofix", action="store_true", required=False)

        add_argument(
            "--no-checkpoint-warning-decorators",
            default="asynccontextmanager",
            required=False,
            type=comma_separated_list,
            help=(
                "Comma-separated list of decorators to disable TRIO910 & TRIO911 "
                "checkpoint warnings for. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
                "For example, ``--no-checkpoint-warning-decorators=app.route,"
                "mydecorator,mypackage.mydecorators.*``"
            ),
        )
        add_argument(
            "--startable-in-context-manager",
            type=parse_trio114_identifiers,
            default="",
            required=False,
            help=(
                "Comma-separated list of method calls to additionally enable TRIO113 "
                "warnings for. Will also check for the pattern inside function calls. "
                "Methods must be valid identifiers as per `str.isidientifier()` and "
                "not reserved keywords. "
                "For example, ``--startable-in-context-manager=worker_serve,"
                "myfunction``"
            ),
        )
        add_argument(
            "--trio200-blocking-calls",
            type=parse_trio200_dict,
            default={},
            required=False,
            help=(
                "Comma-separated list of key->value pairs, where key is a [dotted] "
                "function that if found inside an async function will raise TRIO200, "
                "suggesting it be replaced with {value}"
            ),
        )
        add_argument(
            "--enable-visitor-codes-regex",
            type=re.compile,  # type: ignore[arg-type]
            default=".*",
            required=False,
            help=(
                "Regex string of visitors to enable. Can be used to disable broken "
                "visitors, or instead of --select/--disable to select error codes "
                "in a way that is more performant. If a visitor raises multiple codes "
                "it will not be disabled unless all codes are disabled, but it will "
                "not report codes matching this regex."
            ),
        )
        add_argument(
            "--anyio",
            # action=store_true + parse_from_config does seem to work here, despite
            # https://github.com/PyCQA/flake8/issues/1770
            action="store_true",
            required=False,
            default=False,
            help=(
                "Change the default library to be anyio instead of trio."
                " If trio is imported it will assume both are available and print"
                " suggestions with [anyio|trio]."
            ),
        )

    @staticmethod
    def parse_options(options: Namespace):
        Plugin.options = options


def comma_separated_list(raw_value: str) -> list[str]:
    return [s.strip() for s in raw_value.split(",") if s.strip()]


def parse_trio114_identifiers(raw_value: str) -> list[str]:
    values = comma_separated_list(raw_value)
    for value in values:
        if keyword.iskeyword(value) or not value.isidentifier():
            raise ArgumentTypeError(f"{value!r} is not a valid method identifier")
    return values


def parse_trio200_dict(raw_value: str) -> dict[str, str]:
    res: dict[str, str] = {}
    splitter = "->"  # avoid ":" because it's part of .ini file syntax
    values = [s.strip() for s in raw_value.split(",") if s.strip()]

    for value in values:
        split_values = list(map(str.strip, value.split(splitter)))
        if len(split_values) != 2:
            # argparse will eat this error message and spit out it's own
            # if we raise it as ValueError
            raise ArgumentTypeError(
                f"Invalid number ({len(split_values)-1}) of splitter "
                + f"tokens {splitter!r} in {value!r}"
            )
        res[split_values[0]] = split_values[1]
    return res

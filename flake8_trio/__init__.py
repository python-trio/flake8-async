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
import subprocess
import sys
import tokenize
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import TYPE_CHECKING

import libcst as cst

from .base import Options
from .runner import Flake8TrioRunner, Flake8TrioRunner_cst
from .visitors import ERROR_CLASSES, ERROR_CLASSES_CST, default_disabled_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from os import PathLike

    from flake8.options.manager import OptionManager

    from .base import Error


# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "23.5.1"


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
    parser = ArgumentParser(prog="flake8-trio")
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
        if plugin.options.autofix_codes:
            with open(file, "w") as file:
                file.write(plugin.module.code)
    return 1 if any_error else 0


class Plugin:
    name = __name__
    version = __version__
    standalone = True
    _options: Options | None = None

    @property
    def options(self) -> Options:
        assert self._options is not None
        return self._options

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
        # when run as a flake8 plugin, flake8 handles suppressing errors from `noqa`.
        # it's therefore important we don't suppress any errors for compatibility with
        # flake8-noqa
        if not self.standalone:
            self.options.disable_noqa = True

        cst_runner = Flake8TrioRunner_cst(self.options, self.module)
        # any noqa'd errors are suppressed upon being generated
        yield from cst_runner.run()

        problems_ast = Flake8TrioRunner.run(self._tree, self.options)
        if self.options.disable_noqa:
            yield from problems_ast
            return

        for problem in problems_ast:
            # access the stored noqas in cst_runner
            noqa = cst_runner.noqas.get(problem.line)
            # if there's a noqa comment, and it's bare or this code is listed in it
            if noqa is not None and (noqa == set() or problem.code in noqa):
                continue
            yield problem

        # update saved module so modified source code can be accessed when autofixing
        self.module = cst_runner.module

    @staticmethod
    def add_options(option_manager: OptionManager | ArgumentParser):
        if isinstance(option_manager, ArgumentParser):
            Plugin.standalone = True
            add_argument = option_manager.add_argument
            add_argument(
                nargs="*",
                metavar="file",
                dest="files",
                help="Files(s) to format, instead of autodetection.",
            )
            add_argument(
                "--disable-noqa",
                required=False,
                default=False,
                action="store_true",
                help=(
                    'Disable the effect of "# noqa". This will report errors on '
                    'lines with "# noqa" at the end.'
                ),
            )
        else:  # if run as a flake8 plugin
            Plugin.standalone = False
            # Disable TRIO9xx calls by default
            option_manager.extend_default_ignore(default_disabled_error_codes)
            # add parameter to parse from flake8 config
            add_argument = functools.partial(  # type: ignore
                option_manager.add_option, parse_from_config=True
            )

        add_argument(
            "--enable",
            type=comma_separated_list,
            default="TRIO",
            required=False,
            help=(
                "Comma-separated list of error codes to enable, similar to flake8"
                " --select but is additionally more performant as it will disable"
                " non-enabled visitors from running instead of just silencing their"
                " errors."
            ),
        )
        add_argument(
            "--disable",
            type=comma_separated_list,
            default="TRIO9" if Plugin.standalone else "",
            required=False,
            help=(
                "Comma-separated list of error codes to disable, similar to flake8"
                " --ignore but is additionally more performant as it will disable"
                " non-enabled visitors from running instead of just silencing their"
                " errors."
            ),
        )
        add_argument(
            "--autofix",
            type=comma_separated_list,
            default="",
            required=False,
            help=(
                "Comma-separated list of error-codes to enable autofixing for"
                "if implemented. Requires running as a standalone program."
            ),
        )
        add_argument(
            "--error-on-autofix",
            action="store_true",
            required=False,
            default=False,
            help="Whether to also print an error message for autofixed errors",
        )
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
        def get_matching_codes(
            patterns: Iterable[str], codes: Iterable[str]
        ) -> Iterable[str]:
            for pattern in patterns:
                for code in codes:
                    if code.lower().startswith(pattern.lower()):
                        yield code

        all_codes: set[str] = {
            err_code
            for err_class in (*ERROR_CLASSES, *ERROR_CLASSES_CST)
            for err_code in err_class.error_codes.keys()  # type: ignore[attr-defined]
            if len(err_code) == 7  # exclude e.g. TRIO103_anyio_trio
        }

        if options.autofix and not Plugin.standalone:
            print("Cannot autofix when run as a flake8 plugin.", file=sys.stderr)
            sys.exit(1)
        autofix_codes = set(get_matching_codes(options.autofix, all_codes))

        # enable codes
        enabled_codes = set(get_matching_codes(options.enable, all_codes))

        # disable codes
        enabled_codes -= set(get_matching_codes(options.disable, enabled_codes))

        # if disable has default value, re-enable explicitly enabled codes
        if options.disable == ["TRIO9"]:
            enabled_codes.update(code for code in options.enable if len(code) == 7)

        Plugin._options = Options(
            enabled_codes=enabled_codes,
            autofix_codes=autofix_codes,
            error_on_autofix=options.error_on_autofix,
            no_checkpoint_warning_decorators=options.no_checkpoint_warning_decorators,
            startable_in_context_manager=options.startable_in_context_manager,
            trio200_blocking_calls=options.trio200_blocking_calls,
            anyio=options.anyio,
            disable_noqa=options.disable_noqa,
        )


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

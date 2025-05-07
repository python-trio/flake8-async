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
import warnings
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import TYPE_CHECKING

import libcst as cst

from .base import Options, error_has_subidentifier
from .runner import Flake8AsyncRunner, Flake8AsyncRunner_cst
from .visitors import ERROR_CLASSES, ERROR_CLASSES_CST, default_disabled_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from os import PathLike

    from flake8.options.manager import OptionManager

    from .base import Error


# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "25.5.2"


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
    parser = ArgumentParser(prog="flake8-async")
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

    def __init__(
        self, tree: ast.AST, lines: Sequence[str], filename: str | None = None
    ):
        super().__init__()
        self.filename: str | None = filename
        self._tree = tree
        source = "".join(lines)

        self.module: cst.Module = cst_parse_module_native(source)

    @classmethod
    def from_filename(cls, filename: str | PathLike[str]) -> Plugin:
        # only used with --runslow
        with tokenize.open(filename) as f:
            source = f.read()
        return cls.from_source(source, filename=filename)

    # alternative `__init__` to avoid re-splitting and/or re-joining lines
    @classmethod
    def from_source(
        cls, source: str, filename: str | PathLike[str] | None = None
    ) -> Plugin:
        plugin = Plugin.__new__(cls)
        super(Plugin, plugin).__init__()
        plugin._tree = ast.parse(source)
        plugin.filename = str(filename) if filename else None
        plugin.module = cst_parse_module_native(source)
        return plugin

    def run(self) -> Iterable[Error]:
        # when run as a flake8 plugin, flake8 handles suppressing errors from `noqa`.
        # it's therefore important we don't suppress any errors for compatibility with
        # flake8-noqa
        if not self.standalone:
            self.options.disable_noqa = True

        cst_runner = Flake8AsyncRunner_cst(self.options, self.module)
        # any noqa'd errors are suppressed upon being generated
        yield from cst_runner.run()

        problems_ast = Flake8AsyncRunner.run(self._tree, self.options)
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
        else:  # pragma: no-cov-no-flake8
            Plugin.standalone = False
            # Disable ASYNC9xx calls by default
            option_manager.extend_default_ignore(default_disabled_error_codes)
            # add parameter to parse from flake8 config
            add_argument = functools.partial(  # type: ignore
                option_manager.add_option, parse_from_config=True
            )

        add_argument(
            "--enable",
            type=comma_separated_list,
            default="ASYNC",
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
            default="ASYNC9" if Plugin.standalone else "",
            required=False,
            help=(
                "Comma-separated list of error codes to disable, similar to flake8"
                " --ignore but is additionally more performant as it will disable"
                " non-enabled visitors from running instead of just silencing their"
                " errors."
            ),
        )
        add_argument(
            "--per-file-disable",
            type=parse_per_file_disable,
            default={},
            required=False,
            help=("..."),
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
                "Comma-separated list of decorators to disable ASYNC910 & ASYNC911 "
                "checkpoint warnings for. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
                "For example, ``--no-checkpoint-warning-decorators=app.route,"
                "mydecorator,mypackage.mydecorators.*``"
            ),
        )
        add_argument(
            "--transform-async-generator-decorators",
            default="",
            required=False,
            type=comma_separated_list,
            help=(
                "Comma-separated list of decorators to disable ASYNC900 warnings for. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
                "For example, ``--transform-async-generator-decorators=fastapi.Depends,"
                "trio_util.trio_async_generator``"
            ),
        )
        add_argument(
            "--exception-suppress-context-managers",
            default="",
            required=False,
            type=comma_separated_list,
            help=(
                "Comma-separated list of contextmanagers which may suppress exceptions "
                "without reraising, breaking checkpoint guarantees of ASYNC91x. "
                "``contextlib.suppress`` will be added to the list. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
            ),
        )
        add_argument(
            "--startable-in-context-manager",
            type=parse_async114_identifiers,
            default="",
            required=False,
            help=(
                "Comma-separated list of method calls to additionally enable ASYNC113 "
                "warnings for. Will also check for the pattern inside function calls. "
                "Methods must be valid identifiers as per `str.isidientifier()` and "
                "not reserved keywords. "
                "For example, ``--startable-in-context-manager=worker_serve,"
                "myfunction``"
            ),
        )
        add_argument(
            "--trio200-blocking-calls",
            type=parse_async200_dict,
            default={},
            required=False,
            help=(
                "Comma-separated list of key->value pairs, where key is a [dotted] "
                "function that if found inside an async function will raise ASYNC200, "
                "suggesting it be replaced with {value}"
            ),
        )
        add_argument(
            "--async200-blocking-calls",
            type=parse_async200_dict,
            default={},
            required=False,
            help=(
                "Comma-separated list of key->value pairs, where key is a [dotted] "
                "function that if found inside an async function will raise ASYNC200, "
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
                "Change the default library for suggestions to be anyio instead of trio."
                " If asyncio/trio is imported it will assume that is also available and"
                " print suggestions with [asyncio/anyio/trio]."
            ),
        )
        add_argument(
            "--asyncio",
            # action=store_true + parse_from_config does seem to work here, despite
            # https://github.com/PyCQA/flake8/issues/1770
            action="store_true",
            required=False,
            default=False,
            help=(
                "Change the default library for suggestions to be asyncio instead of"
                " trio."
                " If anyio/trio is imported it will assume that is also available and"
                " print suggestions with [asyncio/anyio/trio]."
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
            for err_code in err_class.error_codes  # type: ignore[attr-defined]
            if not error_has_subidentifier(err_code)  # exclude e.g. ASYNC103_anyio_trio
        }
        assert all_codes

        if options.autofix and not Plugin.standalone:  # pragma: no-cov-no-flake8
            print("Cannot autofix when run as a flake8 plugin.", file=sys.stderr)
            sys.exit(1)
        autofix_codes = set(get_matching_codes(options.autofix, all_codes))

        # enable codes
        enabled_codes = set(get_matching_codes(options.enable, all_codes))

        # disable codes
        enabled_codes -= set(get_matching_codes(options.disable, enabled_codes))

        # if disable has default value, re-enable explicitly enabled codes
        if options.disable == ["ASYNC9"]:
            enabled_codes.update(
                code for code in options.enable if not error_has_subidentifier(code)
            )

        # we do not use DeprecationWarning, since that is silenced when run as standalone
        # or should maybe just print on stderr
        if options.trio200_blocking_calls:
            warnings.warn(
                "trio200-blocking-calls has been deprecated in favor "
                "of async200-blocking-calls",
                stacklevel=1,
            )
            assert not options.async200_blocking_calls, (
                "You cannot specify both trio200-blocking-calls and "
                "async200-blocking-calls. You should only use the latter."
            )
            options.async200_blocking_calls = options.trio200_blocking_calls

        Plugin._options = Options(
            enabled_codes=enabled_codes,
            autofix_codes=autofix_codes,
            error_on_autofix=options.error_on_autofix,
            no_checkpoint_warning_decorators=options.no_checkpoint_warning_decorators,
            transform_async_generator_decorators=options.transform_async_generator_decorators,
            exception_suppress_context_managers=options.exception_suppress_context_managers,
            startable_in_context_manager=options.startable_in_context_manager,
            async200_blocking_calls=options.async200_blocking_calls,
            anyio=options.anyio,
            asyncio=options.asyncio,
            disable_noqa=options.disable_noqa,
        )


def comma_separated_list(raw_value: str) -> list[str]:
    return [s.strip() for s in raw_value.split(",") if s.strip()]


def parse_async114_identifiers(raw_value: str) -> list[str]:
    values = comma_separated_list(raw_value)
    for value in values:
        if keyword.iskeyword(value) or not value.isidentifier():
            raise ArgumentTypeError(f"{value!r} is not a valid method identifier")
    return values


def parse_async200_dict(raw_value: str) -> dict[str, str]:
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
                f"tokens {splitter!r} in {value!r}"
            )
        res[split_values[0]] = split_values[1]
    return res


# not run if flake8 is installed
# TODO: this is not tested at all atm, I'm not even sure if it works
def parse_per_file_disable(  # pragma: no cover
    raw_value: str,
) -> dict[str, tuple[str, ...]]:
    res: dict[str, tuple[str, ...]] = {}
    splitter = "->"
    values = [s.strip() for s in raw_value.split(" \t\n") if s.strip()]
    for value in values:
        split_values = list(map(str.strip, value.split(splitter)))
        if len(split_values) != 2:
            # argparse will eat this error message and spit out its own
            # if we raise it as ValueError
            raise ArgumentTypeError(
                f"Invalid number ({len(split_values)-1}) of splitter "
                f"tokens {splitter!r} in {value!r}"
            )
        res[split_values[0]] = tuple(split_values[1].split(","))
    return res

"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

from __future__ import annotations

import ast
import keyword
import re
import tokenize
from argparse import ArgumentTypeError, Namespace
from typing import TYPE_CHECKING

from .runner import Flake8TrioRunner
from .visitors import default_disabled_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable
    from os import PathLike

    from flake8.options.manager import OptionManager

    from .base import Error


# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "23.2.4"


class Plugin:
    name = __name__
    version = __version__
    options: Namespace = Namespace()

    def __init__(self, tree: ast.AST):
        self._tree = tree

    @classmethod
    def from_filename(cls, filename: str | PathLike[str]) -> Plugin:  # pragma: no cover
        # only used with --runslow
        with tokenize.open(filename) as f:
            source = f.read()
        return cls(ast.parse(source))

    def run(self) -> Iterable[Error]:
        yield from Flake8TrioRunner.run(self._tree, self.options)

    @staticmethod
    def add_options(option_manager: OptionManager):
        # Disable TRIO9xx calls
        option_manager.extend_default_ignore(default_disabled_error_codes)

        option_manager.add_option(
            "--no-checkpoint-warning-decorators",
            default="asynccontextmanager",
            parse_from_config=True,
            required=False,
            comma_separated_list=True,
            help=(
                "Comma-separated list of decorators to disable TRIO910 & TRIO911 "
                "checkpoint warnings for. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
                "For example, ``--no-checkpoint-warning-decorators=app.route,"
                "mydecorator,mypackage.mydecorators.*``"
            ),
        )
        option_manager.add_option(
            "--startable-in-context-manager",
            type=parse_trio114_identifiers,
            default="",
            parse_from_config=True,
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
        option_manager.add_option(
            "--trio200-blocking-calls",
            type=parse_trio200_dict,
            default={},
            parse_from_config=True,
            required=False,
            help=(
                "Comma-separated list of key->value pairs, where key is a [dotted] "
                "function that if found inside an async function will raise TRIO200, "
                "suggesting it be replaced with {value}"
            ),
        )
        option_manager.add_option(
            "--enable-visitor-codes-regex",
            type=re.compile,
            default=".*",
            parse_from_config=True,
            required=False,
            help=(
                "Regex string of visitors to enable. Can be used to disable broken "
                "visitors, or instead of --select/--disable to select error codes "
                "in a way that is more performant. If a visitor raises multiple codes "
                "it will not be disabled unless all codes are disabled, but it will "
                "not report codes matching this regex."
            ),
        )
        option_manager.add_option(
            "--anyio",
            # action=store_true + parse_from_config does seem to work here, despite
            # https://github.com/PyCQA/flake8/issues/1770
            action="store_true",
            parse_from_config=True,
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


# flake8 ignores type parameters if using comma_separated_list
# so we need to reimplement that ourselves if we want to use "type"
# to check values
def parse_trio114_identifiers(raw_value: str) -> list[str]:
    values = [s.strip() for s in raw_value.split(",") if s.strip()]
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
                f"tokens {splitter!r} in {value!r}",
            )
        res[split_values[0]] = split_values[1]
    return res

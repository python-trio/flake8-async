"""Contains base classes used across multiple parts of the package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Collection


# strip the sub-identifier on error used to specify which message to print, when
# several different ones are used for the same code. Used in e.g. Visitor103
def strip_error_subidentifier(s: str) -> str:
    """Turn e.g. ASYNC103_anyio_trio => ASYNC103."""
    return s.split("_")[0]


def error_has_subidentifier(s: str) -> bool:
    return "_" in s


@dataclass
class Options:
    # error codes to give errors for
    enabled_codes: set[str]
    # error codes to autofix
    autofix_codes: set[str]
    # whether to print an error message even when autofixed
    error_on_autofix: bool
    no_checkpoint_warning_decorators: Collection[str]
    transform_async_generator_decorators: Collection[str]
    exception_suppress_context_managers: Collection[str]
    startable_in_context_manager: Collection[str]
    async200_blocking_calls: dict[str, str]
    anyio: bool
    asyncio: bool
    disable_noqa: bool


class Statement(NamedTuple):
    name: str
    lineno: int
    col_offset: int = -1

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Statement)
            and self.name == other.name
            and self.lineno == other.lineno
            and (
                self.col_offset == other.col_offset
                or -1 in (self.col_offset, other.col_offset)
            )
        )

    # Objects that are equal needs to have the same hash, so we don't hash on
    # `col_offset` since it's a "wildcard" value
    def __hash__(self) -> int:
        return hash((self.name, self.lineno))


class Error:
    def __init__(
        self, error_code: str, lineno: int, col: int, message: str, *args: object
    ):
        super().__init__()
        self.line = lineno
        self.col = col
        self.code = error_code
        self.message = message
        self.args = args

    def format_message(self):
        return f"{self.code} " + self.message.format(*self.args)

    # for yielding to flake8
    def __iter__(self):
        yield self.line
        yield self.col
        yield self.format_message()
        # We are no longer yielding `type(Plugin)` since that's quite tricky to do
        # without circular imports, and afaik flake8 doesn't care anymore.
        yield None

    def cmp(self):
        # column may be ignored/modified when autofixing, so sort on that last
        return self.line, self.code, self.args, self.message, self.col

    # for sorting in tests
    def __lt__(self, other: Error) -> bool:
        assert isinstance(other, Error)
        return self.cmp() < other.cmp()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Error) and self.cmp() == other.cmp()

    def __repr__(self) -> str:  # pragma: no cover
        trailer = "".join(f", {x!r}" for x in self.args)
        return f"<{self.code} error at {self.line}:{self.col}{trailer}>"

    def __str__(self) -> str:
        # flake8 adds 1 to the yielded column from `__iter__`, so we do the same here
        return f"{self.line}:{self.col+1}: {self.format_message()}"

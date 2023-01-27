"""Contains base classes used across multiple parts of the package."""

from __future__ import annotations

from typing import Any, NamedTuple


class Statement(NamedTuple):
    name: str
    lineno: int
    col_offset: int = -1

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Statement)
            and self[:2] == other[:2]  # type: ignore
            and (
                self.col_offset == other.col_offset
                or -1 in (self.col_offset, other.col_offset)
            )
        )


class Error:
    def __init__(
        self, error_code: str, lineno: int, col: int, message: str, *args: object
    ):
        self.line = lineno
        self.col = col
        self.code = error_code
        self.message = message
        self.args = args

    # for yielding to flake8
    def __iter__(self):
        yield self.line
        yield self.col
        yield f"{self.code} " + self.message.format(*self.args)
        # We are no longer yielding `type(Plugin)` since that's quite tricky to do
        # without circular imports, and afaik flake8 doesn't care anymore.
        yield None

    def cmp(self):
        return self.line, self.col, self.code, self.args

    # for sorting in tests
    def __lt__(self, other: Any) -> bool:
        assert isinstance(other, Error)
        return self.cmp() < other.cmp()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Error) and self.cmp() == other.cmp()

    def __repr__(self) -> str:  # pragma: no cover
        trailer = "".join(f", {x!r}" for x in self.args)
        return f"<{self.code} error at {self.line}:{self.col}{trailer}>"

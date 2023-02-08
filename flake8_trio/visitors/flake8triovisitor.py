"""Contains the base class that all error classes inherit from."""

from __future__ import annotations

import ast
import re
from abc import ABC
from typing import TYPE_CHECKING, Any, Union

from ..base import Error, Statement

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..runner import SharedState

    HasLineCol = Union[
        ast.expr, ast.stmt, ast.arg, ast.excepthandler, ast.alias, Statement
    ]


class Flake8TrioVisitor(ast.NodeVisitor, ABC):
    # abstract attribute by not providing a value
    error_codes: dict[str, str]

    def __init__(self, shared_state: SharedState):
        super().__init__()
        assert self.error_codes, "subclass must define error_codes"
        self.outer: dict[ast.AST, dict[str, Any]] = {}
        self.novisit = False
        self.__state = shared_state

        self.options = self.__state.options
        self.typed_calls = self.__state.typed_calls

        # mark variables that shouldn't be saved/loaded in self.get_state
        self.nocopy = {
            "_Flake8TrioVisitor__state",
            "error_codes",
            "nocopy",
            "novisit",
            "options",
            "outer",
            "typed_calls",
        }

        self.suppress_errors = False

    # `variables` can be saved/loaded, but need a setter to not clear the reference
    @property
    def variables(self):
        return self.__state.variables

    @variables.setter
    def variables(self, value):
        self.__state.variables.clear()
        self.__state.variables.update(value)

    def visit(self, node: ast.AST):
        """Visit a node."""
        # construct visitor for this node type
        visitor = getattr(self, "visit_" + node.__class__.__name__, None)

        # if we have a visitor for it, visit it
        # it will set self.novisit if it manually visits children
        self.novisit = False

        if visitor is not None:
            visitor(node)

        # if it doesn't set novisit, let the regular NodeVisitor iterate through
        # subfields
        if not self.novisit:
            super().generic_visit(node)

        # if an outer state was saved in this node restore it after visiting children
        self.set_state(self.outer.pop(node, {}))

        # set novisit so external runner doesn't visit this node with this class
        self.novisit = True

    def visit_nodes(self, *nodes: ast.AST | Iterable[ast.AST]):
        for arg in nodes:
            if isinstance(arg, ast.AST):
                self.visit(arg)
            else:
                for node in arg:
                    self.visit(node)

    def error(
        self,
        node: HasLineCol,
        *args: str | Statement | int,
        error_code: str | None = None,
    ):
        if error_code is None:
            assert (
                len(self.error_codes) == 1
            ), "No error code defined, but class has multiple codes"
            error_code = next(iter(self.error_codes))
        # don't emit an error if this code is disabled in a multi-code visitor
        elif not re.match(self.options.enable_visitor_codes_regex, error_code):
            return

        if not self.suppress_errors:
            self.__state.problems.append(
                Error(
                    # 7 == len('TRIO...'), so alt messages raise the original code
                    error_code[:7],
                    node.lineno,
                    node.col_offset,
                    self.error_codes[error_code],
                    *args,
                )
            )

    def get_state(self, *attrs: str, copy: bool = False) -> dict[str, Any]:
        if not attrs:
            # get all attributes, unless they're marked as nocopy
            attrs = tuple(set(self.__dict__.keys()) - self.nocopy)
        res: dict[str, Any] = {}
        for attr in attrs:
            value = getattr(self, attr)
            if copy and hasattr(value, "copy"):
                value = value.copy()
            res[attr] = value
        return res

    def set_state(self, attrs: dict[str, Any], copy: bool = False):
        for attr, value in attrs.items():
            if copy and hasattr(value, "copy"):
                value = value.copy()
            setattr(self, attr, value)

    def save_state(self, node: ast.AST, *attrs: str, copy: bool = False):
        state = self.get_state(*attrs, copy=copy)
        if node in self.outer:
            # not currently used, and not gonna bother adding dedicated test
            # visitors atm
            self.outer[node].update(state)  # pragma: no cover
        else:
            self.outer[node] = state

    def walk(self, *body: ast.AST) -> Iterable[ast.AST]:
        for b in body:
            yield from ast.walk(b)

    @property
    def library(self) -> tuple[str, ...]:
        return self.__state.library if self.__state.library else ("trio",)

    @property
    def library_str(self) -> str:
        if len(self.library) == 1:
            return self.library[0]
        return "[" + "|".join(self.library) + "]"

    def add_library(self, name) -> None:
        if name not in self.__state.library:
            self.__state.library = self.__state.library + (name,)

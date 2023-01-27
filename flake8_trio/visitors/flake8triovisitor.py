"""Contains the base class that all error classes inherit from."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, Any, Union, cast

from ..base import Error, Statement

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    HasLineCol = Union[ast.expr, ast.stmt, ast.arg, ast.excepthandler, Statement]


class Flake8TrioVisitor(ast.NodeVisitor):
    # abstract attribute by not providing a value
    error_codes: dict[str, str]

    def __init__(self, options: Namespace, _problems: list[Error]):
        super().__init__()
        assert self.error_codes, "subclass must define error_codes"
        self._problems = _problems
        self.suppress_errors = False
        self.options = options
        self.outer: dict[ast.AST, dict[str, Any]] = {}
        self.novisit = False

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
            self._problems.append(
                Error(
                    error_code,
                    node.lineno,
                    node.col_offset,
                    self.error_codes[error_code],
                    *args,
                )
            )

    def get_state(self, *attrs: str, copy: bool = False) -> dict[str, Any]:
        if not attrs:
            attrs = cast(
                tuple[str, ...],
                set(self.__dict__.keys())
                - {"_problems", "options", "outer", "novisit", "error_codes"},
                # TODO: write something clean so don't need to hardcode
            )
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
        self.outer[node] = self.get_state(*attrs, copy=copy)

    def walk(self, *body: ast.AST) -> Iterable[ast.AST]:
        for b in body:
            yield from ast.walk(b)

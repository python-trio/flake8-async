"""Contains visitor for TRIO101.

`yield` inside a nursery or cancel scope is only safe when implementing a context manager
- otherwise, it breaks exception handling.
"""
from __future__ import annotations

from typing import Any

import libcst as cst
import libcst.matchers as m

from .flake8triovisitor import Flake8TrioVisitor_cst
from .helpers import (
    cancel_scope_names,
    error_class_cst,
    func_has_decorator,
    with_has_call,
)


@error_class_cst
class Visitor101(Flake8TrioVisitor_cst):
    error_codes = {
        "TRIO101": (
            "`yield` inside a nursery or cancel scope is only safe when implementing "
            "a context manager - otherwise, it breaks exception handling."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._yield_is_error = False
        self._safe_decorator = False

    def visit_With(self, node: cst.With):
        self.save_state(node, "_yield_is_error", copy=True)
        # if there's no safe decorator,
        # and it's not yet been determined that yield is error
        # and this withitem opens a cancelscope:
        # then yielding is unsafe
        self._yield_is_error = (
            not self._safe_decorator
            and not self._yield_is_error
            and bool(with_has_call(node, "open_nursery", *cancel_scope_names))
        )

    @m.leave(m.OneOf(m.With(), m.FunctionDef()))
    def restore_state(
        self, original_node: cst.BaseStatement, updated_node: cst.BaseStatement
    ) -> cst.BaseStatement:
        self.set_state(self.outer.pop(original_node, {}))
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef):
        self.save_state(node, "_yield_is_error", "_safe_decorator")
        self._yield_is_error = False
        self._safe_decorator = func_has_decorator(
            node, "contextmanager", "asynccontextmanager", "fixture"
        )

    def visit_Yield(self, node: cst.Yield):
        if self._yield_is_error:
            self.error(node)

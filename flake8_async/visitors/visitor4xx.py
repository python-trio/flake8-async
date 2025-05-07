"""4XX error classes, which handle exception groups.

ASYNC400 except-star-invalid-attribute checks for invalid attribute access on except*
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import error_class

if TYPE_CHECKING:
    from collections.abc import Mapping

EXCGROUP_ATTRS = (
    # from ExceptionGroup
    "message",
    "exceptions",
    "subgroup",
    "split",
    "derive",
    # from BaseException
    "args",
    "with_traceback",
    "add_note",
    # in the backport
    "_is_protocol",
)


@error_class
class Visitor4xx(Flake8AsyncVisitor):

    error_codes: Mapping[str, str] = {
        "ASYNC400": (
            "Accessing attribute {} on ExceptionGroup as if it was a bare Exception."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.exception_groups: list[str] = []
        self.trystar = False

    def visit_TryStar(self, node: ast.TryStar):  # type: ignore[name-defined]
        self.save_state(node, "trystar")
        self.trystar = True

    def visit_Try(self, node: ast.Try):
        self.save_state(node, "trystar")
        self.trystar = False

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if not self.trystar or node.name is None:
            return
        self.save_state(node, "exception_groups", copy=True)
        self.exception_groups.append(node.name)
        self.visit_nodes(node.body)

    def visit_Attribute(self, node: ast.Attribute):
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in self.exception_groups
            and node.attr not in EXCGROUP_ATTRS
            and not (node.attr.startswith("__") and node.attr.endswith("__"))
        ):
            self.error(node, node.attr)

    def _clear_if_name(self, node: ast.AST | None):
        if isinstance(node, ast.Name) and node.id in self.exception_groups:
            self.exception_groups.remove(node.id)

    def _walk_and_clear(self, node: ast.AST | None):
        if node is None:
            return
        for n in ast.walk(node):
            self._clear_if_name(n)

    def visit_Assign(self, node: ast.Assign):
        for t in node.targets:
            self._walk_and_clear(t)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self._clear_if_name(node.target)

    def visit_withitem(self, node: ast.withitem):
        self._walk_and_clear(node.optional_vars)

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    ):
        self.save_state(node, "exception_groups", "trystar", copy=False)
        self.exception_groups = []

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

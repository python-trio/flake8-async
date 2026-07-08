"""4XX error classes, which handle exception groups.

ASYNC400 except-star-invalid-attribute checks for invalid attribute access on except*
ASYNC401 pytest-raises-exception-group checks for pytest.raises(ExceptionGroup)
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import disabled_by_default, error_class

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


EXCGROUP_QUALNAMES = (
    "ExceptionGroup",
    "BaseExceptionGroup",
    "builtins.ExceptionGroup",
    "builtins.BaseExceptionGroup",
    "exceptiongroup.ExceptionGroup",
    "exceptiongroup.BaseExceptionGroup",
)


@error_class
@disabled_by_default
class Visitor401(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC401": (
            "Use `pytest.RaisesGroup` instead of `pytest.raises({})` when expecting"
            " exception groups."
        )
    }

    def _exception_group_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Tuple):
            for elt in node.elts:
                if name := self._exception_group_name(elt):
                    return name
            return None

        canonical = self.canonical_name(node)
        if canonical in EXCGROUP_QUALNAMES:
            return ast.unparse(node)
        return None

    def _expected_exception_arg(self, node: ast.Call) -> ast.expr | None:
        if node.args:
            return node.args[0]
        for kw in node.keywords:
            if kw.arg == "expected_exception":
                return kw.value
        return None

    def visit_Call(self, node: ast.Call):
        if (
            self.canonical_name(node.func) == "pytest.raises"
            and (expected_exception := self._expected_exception_arg(node)) is not None
            and (exception_group := self._exception_group_name(expected_exception))
        ):
            self.error(node, exception_group)

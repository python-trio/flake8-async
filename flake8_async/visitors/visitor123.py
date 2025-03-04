"""foo."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import error_class

if TYPE_CHECKING:
    from collections.abc import Mapping


@error_class
class Visitor123(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC123": (
            "Raising a child exception of an exception group loses"
            " context, cause, and/or traceback of the exception inside the group."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.try_star = False
        self.exception_group_names: set[str] = set()
        self.child_exception_list_names: set[str] = set()
        self.child_exception_names: set[str] = set()

    def _is_exception_group(self, node: ast.expr) -> bool:
        return (
            (isinstance(node, ast.Name) and node.id in self.exception_group_names)
            or (
                # a child exception might be an ExceptionGroup
                self._is_child_exception(node)
            )
            or (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and self._is_exception_group(node.func.value)
                and node.func.attr in ("subgroup", "split")
            )
        )

    def _is_exception_list(self, node: ast.expr | None) -> bool:
        return (
            isinstance(node, ast.Name) and node.id in self.child_exception_list_names
        ) or (
            isinstance(node, ast.Attribute)
            and node.attr == "exceptions"
            and self._is_exception_group(node.value)
        )

    def _is_child_exception(self, node: ast.expr | None) -> bool:
        return (
            isinstance(node, ast.Name) and node.id in self.child_exception_names
        ) or (isinstance(node, ast.Subscript) and self._is_exception_list(node.value))

    def visit_Raise(self, node: ast.Raise):
        if self._is_child_exception(node.exc):
            self.error(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.save_state(
            node,
            "exception_group_names",
            "child_exception_list_names",
            "child_exception_names",
            copy=True,
        )
        if node.name is None or (
            not self.try_star
            and (node.type is None or "ExceptionGroup" not in ast.unparse(node.type))
        ):
            self.novisit = True
            return
        self.exception_group_names = {node.name}

    # ast.TryStar added in py311
    def visit_TryStar(self, node: ast.TryStar):  # type: ignore[name-defined]  # pragma: no-cov-py-lt-311
        self.save_state(node, "try_star", copy=False)
        self.try_star = True

    def visit_Assign(self, node: ast.Assign | ast.AnnAssign):
        if node.value is None or not self.exception_group_names:
            return
        targets = (node.target,) if isinstance(node, ast.AnnAssign) else node.targets
        if self._is_child_exception(node.value):
            # not normally possible to assign single exception to multiple targets
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                self.child_exception_names.add(targets[0].id)
        elif self._is_exception_list(node.value):
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                self.child_exception_list_names.add(targets[0].id)
            # unpacking tuples and Starred and shit. Not implemented
        elif self._is_exception_group(node.value):
            for target in targets:
                if isinstance(target, ast.Name):
                    self.exception_group_names.add(target.id)
                elif isinstance(target, ast.Tuple):
                    for t in target.elts:
                        if isinstance(t, ast.Name):
                            self.exception_group_names.add(t.id)

    visit_AnnAssign = visit_Assign

    def visit_For(self, node: ast.For):
        if self._is_exception_list(node.iter) and isinstance(node.target, ast.Name):
            self.child_exception_names.add(node.target.id)

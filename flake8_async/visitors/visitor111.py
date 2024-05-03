"""Contains Visitor111 which looks for incorrectly nested nurseries."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, NamedTuple

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import error_class, get_matching_call

if TYPE_CHECKING:
    from collections.abc import Mapping


def is_nursery_like(node: ast.expr) -> bool:
    return bool(
        get_matching_call(node, "open_nursery", base="trio")
        or get_matching_call(node, "create_task_group", base="anyio")
        or get_matching_call(node, "TaskGroup", base="asyncio")
    )


@error_class
class Visitor111(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC111": (
            "variable {2} is usable within the context manager on line {0}, but that "
            "will close before nursery/taskgroup opened on line {1} - this is usually "
            "a bug. Nursery/TaskGroup should generally be the inner-most context manager."
        ),
    }

    class NurseryCall(NamedTuple):
        stack_index: int
        name: str

    class TrioContextManager(NamedTuple):
        lineno: int
        name: str
        is_nursery: bool

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._context_managers: list[Visitor111.TrioContextManager] = []
        self._nursery_call: Visitor111.NurseryCall | None = None

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_context_managers", copy=True)
        for item in node.items:
            # 111
            # if a withitem is saved in a variable,
            # push its line, variable, and whether it's a trio nursery
            # to the _context_managers stack,
            if isinstance(item.optional_vars, ast.Name):
                self._context_managers.append(
                    self.TrioContextManager(
                        item.context_expr.lineno,
                        item.optional_vars.id,
                        is_nursery_like(item.context_expr),
                    )
                )

    visit_AsyncWith = visit_With

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    ):
        self.save_state(node)
        self._context_managers = []
        self._nursery_call = None

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    # if it's a <X>.start[_soon] call
    # and <X> is a nursery listed in self._context_managers:
    # Save <X>'s index in self._context_managers to guard against cm's higher in the
    # stack being passed as parameters to it. (and save <X> for the error message)
    def visit_Call(self, node: ast.Call):
        self.save_state(node, "_nursery_call")

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr in ("start", "start_soon", "create_task")
        ):
            self._nursery_call = None
            for i, cm in enumerate(self._context_managers):
                if node.func.value.id == cm.name:
                    # don't break upon finding a nursery in case there's multiple cm's
                    # on the stack with the same name
                    if cm.is_nursery:
                        self._nursery_call = self.NurseryCall(i, node.func.attr)
                    else:
                        self._nursery_call = None

    # If we're inside a <X>.start[_soon] call (where <X> is a nursery),
    # and we're accessing a variable cm that's on the self._context_managers stack,
    # with a higher index than <X>:
    #   Raise error since the scope of cm may close before the function passed to the
    # nursery finishes.
    def visit_Name(self, node: ast.Name):
        if self._nursery_call is None:
            return

        for i, cm in enumerate(self._context_managers):
            if cm.name == node.id and i > self._nursery_call.stack_index:
                self.error(
                    node,
                    cm.lineno,
                    self._context_managers[self._nursery_call.stack_index].lineno,
                    node.id,
                    self._nursery_call.name,
                )

"""Contains Visitor102 with ASYNC102 and ASYNC120.

ASYNC102: await-in-finally-or-cancelled
ASYNC120: await-in-except


To properly protect they must be inside a shielded cancel scope with a timeout.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from ..base import Statement
from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import cancel_scope_names, critical_except, error_class, get_matching_call

if TYPE_CHECKING:
    from collections.abc import Mapping


@error_class
class Visitor102(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC102": (
            "await inside {0.name} on line {0.lineno} must have shielded cancel "
            "scope with a timeout."
        ),
        "ASYNC120": (
            "checkpoint inside {0.name} on line {0.lineno} will discard the active "
            "exception if cancelled."
        ),
    }

    class TrioScope:
        def __init__(self, node: ast.Call, funcname: str):
            super().__init__()
            self.node = node
            self.funcname = funcname
            self.variable_name: str | None = None
            self.shielded: bool = False

            # trio 0.27 adds shield parameter to all scope helpers
            if self.funcname in cancel_scope_names:
                for kw in node.keywords:
                    # Only accepts constant values
                    if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                        self.shielded = kw.value.value

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._critical_scope: Statement | None = None
        self._trio_context_managers: list[Visitor102.TrioScope] = []
        self.cancelled_caught = False

        # list of dangerous awaits inside a non-critical except handler,
        # which will emit errors upon reaching a raise.
        # Entries are only added to the list inside except handlers,
        # so with the `save_state` in visit_ExceptHandler any entries not followed
        # by a raise will be thrown out when exiting the except handler.
        self._potential_120: list[
            tuple[ast.Await | ast.AsyncFor | ast.AsyncWith, Statement]
        ] = []

    # if we're inside a finally or critical except, and we're not inside a scope that
    # doesn't have both a timeout and shield
    def async_call_checker(
        self, node: ast.Await | ast.AsyncFor | ast.AsyncWith
    ) -> None:
        if self._critical_scope is not None and not any(
            cm.shielded for cm in self._trio_context_managers
        ):
            # non-critical exception handlers have the statement name set to "except"
            if self._critical_scope.name == "except":
                self._potential_120.append((node, self._critical_scope))
            else:
                self.error(node, self._critical_scope, error_code="ASYNC102")

    def visit_Raise(self, node: ast.Raise):
        for err_node, scope in self._potential_120:
            self.error(err_node, scope, error_code="ASYNC120")
        self._potential_120.clear()

    def is_safe_aclose_call(self, node: ast.Await) -> bool:
        return (
            # don't mark calls safe in asyncio-only files
            # a more defensive option would be `asyncio not in self.library`
            self.library != ("asyncio",)
            and isinstance(node.value, ast.Call)
            # only known safe if no arguments
            and not node.value.args
            and not node.value.keywords
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "aclose"
        )

    def visit_Await(self, node: ast.Await):
        # allow calls to `.aclose()`
        if not (self.is_safe_aclose_call(node)):
            self.async_call_checker(node)

    visit_AsyncFor = async_call_checker

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_trio_context_managers", copy=True)

        # Check for a `with trio.<scope_creator>`
        for item in node.items:
            call = get_matching_call(
                item.context_expr,
                "open_nursery",
                "create_task_group",
                *cancel_scope_names,
            )
            if call is None:
                continue

            trio_scope = self.TrioScope(call.node, call.name)
            # check if it's saved in a variable
            if isinstance(item.optional_vars, ast.Name):
                trio_scope.variable_name = item.optional_vars.id

            self._trio_context_managers.append(trio_scope)
            break

    def visit_AsyncWith(self, node: ast.AsyncWith):
        # trio.open_nursery and anyio.create_task_group are not cancellation points
        # so only treat this as an async call if it contains a call that does not match.
        # asyncio.TaskGroup() appears to be a source of cancellation when exiting.
        for item in node.items:
            if not (
                get_matching_call(item.context_expr, "open_nursery", base="trio")
                or get_matching_call(
                    item.context_expr, "create_task_group", base="anyio"
                )
            ):
                self.async_call_checker(node)
                break
        self.visit_With(node)

    def visit_Try(self, node: ast.Try | ast.TryStar):  # type: ignore[name-defined]
        self.save_state(
            node, "_critical_scope", "_trio_context_managers", "cancelled_caught"
        )
        self.cancelled_caught = False
        # There's no visit_Finally, so we need to manually visit the Try fields.
        self.visit_nodes(node.body, node.handlers, node.orelse)

        self._trio_context_managers = []
        # node.finalbody does not have a lineno, so we give the position of the try
        # it'd be possible to estimate the lineno given the last except and the first
        # statement in the finally, but it would be very hard to get it perfect with
        # comments and empty lines and stuff.
        self._critical_scope = Statement("try/finally", node.lineno, node.col_offset)
        self.visit_nodes(node.finalbody)

    visit_TryStar = visit_Try

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # if we're inside a critical scope, a nested except should never override that
        if self._critical_scope is not None and self._critical_scope.name != "except":
            return

        self.save_state(
            node, "_critical_scope", "_trio_context_managers", "_potential_120"
        )
        self._trio_context_managers = []
        self._potential_120 = []

        if self.cancelled_caught or (res := critical_except(node)) is None:
            self._critical_scope = Statement("except", node.lineno, node.col_offset)
        else:
            self._critical_scope = res
            self.cancelled_caught = True

    def visit_Assign(self, node: ast.Assign):
        # checks for <scopename>.shield = [True/False]
        # and <scopename>.cancel_scope.shield
        # We don't care to differentiate between them depending on if the scope is
        # a nursery or not, so e.g. `cs.cancel_scope.shield`/`nursery.shield` will "work"
        if self._trio_context_managers and len(node.targets) == 1:
            target = node.targets[0]
            for scope in reversed(self._trio_context_managers):
                if (
                    scope.variable_name is not None
                    and isinstance(node.value, ast.Constant)
                    and isinstance(target, ast.Attribute)
                    and target.attr == "shield"
                    and (
                        (
                            isinstance(target.value, ast.Name)
                            and target.value.id == scope.variable_name
                        )
                        or (
                            isinstance(target.value, ast.Attribute)
                            and target.value.attr == "cancel_scope"
                            and isinstance(target.value.value, ast.Name)
                            and target.value.value.id == scope.variable_name
                        )
                    )
                ):
                    scope.shielded = node.value.value

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    ):
        self.save_state(
            node,
            "_critical_scope",
            "_trio_context_managers",
            "_potential_120",
            "cancelled_caught",
        )
        self._critical_scope = None
        self._trio_context_managers = []
        self.cancelled_caught = False

        self._potential_120 = []

        # lambda doesn't have `name` attribute
        if getattr(node, "name", None) == "__aexit__":
            self._critical_scope = Statement("__aexit__", node.lineno, node.col_offset)

    visit_AsyncFunctionDef = visit_FunctionDef
    # lambda can't contain await, try, except, raise, with, or assignments.
    # You also can't do assignment expressions with attributes. So we don't need to
    # do any special handling for them.

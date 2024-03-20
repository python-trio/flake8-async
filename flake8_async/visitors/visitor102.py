"""Visitor102, which warns on unprotected `await` inside `finally`.

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
    }

    class TrioScope:
        def __init__(self, node: ast.Call, funcname: str, _):
            super().__init__()
            self.node = node
            self.funcname = funcname
            self.variable_name: str | None = None
            self.shielded: bool = False
            self.has_timeout: bool = True

            # scope.shielded is assigned to in visit_Assign

            if self.funcname == "CancelScope":
                self.has_timeout = False
                for kw in node.keywords:
                    # Only accepts constant values
                    if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                        self.shielded = kw.value.value
                    # sets to True even if timeout is explicitly set to inf
                    if kw.arg == "deadline":
                        self.has_timeout = True

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._critical_scope: Statement | None = None
        self._trio_context_managers: list[Visitor102.TrioScope] = []
        self.cancelled_caught = False

    # if we're inside a finally or critical except, and we're not inside a scope that
    # doesn't have both a timeout and shield
    def async_call_checker(
        self, node: ast.Await | ast.AsyncFor | ast.AsyncWith
    ) -> None:
        if self._critical_scope is not None and not any(
            cm.has_timeout and cm.shielded for cm in self._trio_context_managers
        ):
            self.error(node, self._critical_scope)

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
                item.context_expr, "open_nursery", *cancel_scope_names
            )
            if call is None:
                continue

            trio_scope = self.TrioScope(*call)
            # check if it's saved in a variable
            if isinstance(item.optional_vars, ast.Name):
                trio_scope.variable_name = item.optional_vars.id

            self._trio_context_managers.append(trio_scope)
            break

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.async_call_checker(node)
        self.visit_With(node)

    def visit_Try(self, node: ast.Try):
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

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if self.cancelled_caught:
            return
        res = critical_except(node)
        if res is None:
            return

        self.save_state(node, "_critical_scope", "_trio_context_managers")
        self.cancelled_caught = True
        self._trio_context_managers = []
        self._critical_scope = res

    def visit_Assign(self, node: ast.Assign):
        # checks for <scopename>.shield = [True/False]
        if self._trio_context_managers and len(node.targets) == 1:
            last_scope = self._trio_context_managers[-1]
            target = node.targets[0]
            if (
                last_scope.variable_name is not None
                and isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == last_scope.variable_name
                and target.attr == "shield"
                and isinstance(node.value, ast.Constant)
            ):
                last_scope.shielded = node.value.value

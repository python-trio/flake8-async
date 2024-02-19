"""Contains visitor for TRIO100.

A `with trio.fail_after(...):` or `with trio.move_on_after(...):`
context does not contain any `await` statements.  This makes it pointless, as
the timeout can only be triggered by a checkpoint.
Checkpoints on Await, Async For and Async With
"""

from __future__ import annotations

from typing import Any

import libcst as cst
import libcst.matchers as m

from .flake8triovisitor import Flake8TrioVisitor_cst
from .helpers import (
    AttributeCall,
    error_class_cst,
    flatten_preserving_comments,
    with_has_call,
)


@error_class_cst
class Visitor100_libcst(Flake8TrioVisitor_cst):
    error_codes = {
        "TRIO100": (
            "{0}.{1} context contains no checkpoints, remove the context or add"
            " `await {0}.lowlevel.checkpoint()`."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_checkpoint_stack: list[bool] = []
        self.node_dict: dict[cst.With, list[AttributeCall]] = {}

    def checkpoint(self) -> None:
        # Set the whole stack to True.
        self.has_checkpoint_stack = [True] * len(self.has_checkpoint_stack)

    def visit_With(self, node: cst.With) -> None:
        if m.matches(node, m.With(asynchronous=m.Asynchronous())):
            self.checkpoint()
        if res := with_has_call(
            node, "fail_after", "fail_at", "move_on_after", "move_on_at", "CancelScope"
        ):
            self.node_dict[node] = res

            self.has_checkpoint_stack.append(False)
        else:
            self.has_checkpoint_stack.append(True)

    def leave_With(
        self, original_node: cst.With, updated_node: cst.With
    ) -> cst.BaseStatement | cst.FlattenSentinel[cst.BaseStatement]:
        if not self.has_checkpoint_stack.pop():
            autofix = len(updated_node.items) == 1
            for res in self.node_dict[original_node]:
                autofix &= self.error(
                    res.node, res.base, res.function
                ) and self.should_autofix(res.node)

            if autofix:
                return flatten_preserving_comments(updated_node)

        return updated_node

    def visit_For(self, node: cst.For):
        if node.asynchronous is not None:
            self.checkpoint()

    def visit_Await(self, node: cst.Await | cst.For | cst.With):
        self.checkpoint()

    def visit_FunctionDef(self, node: cst.FunctionDef):
        self.save_state(node, "has_checkpoint_stack", copy=True)
        self.has_checkpoint_stack = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.restore_state(original_node)
        return updated_node
